import { Router, Request, Response } from 'express';
import pool from '../db';
import { authMiddleware, requireRole } from '../middleware/auth';

const router = Router();
router.use(authMiddleware);

// 处方类型编码映射
const PRESCRIPTION_TYPE_CODES: Record<string, string> = {
  '普通': '01',
  '急诊': '02',
  '儿科': '03',
  '麻醉精一': '04',
  '精二': '05',
};

// 生成处方编号: 类型编码(2) + 日期(8) + 流水号(3) + 校验码(2) = 15位
// 每天每种处方类型独立编号，确保唯一
async function generatePrescriptionCode(type: string, conn: any): Promise<string> {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, '0');
  const d = String(now.getDate()).padStart(2, '0');
  const dateStr = `${y}${m}${d}`;
  const typeCode = PRESCRIPTION_TYPE_CODES[type] || '01';
  const prefix = typeCode + dateStr;

  // 查询当天该类型已有的最大流水号
  const [rows] = await conn.query<any[]>(
    `SELECT MAX(CAST(SUBSTRING(prescription_code, 11, 3) AS UNSIGNED)) as max_seq
     FROM prescriptions
     WHERE prescription_code LIKE ?`,
    [`${prefix}%`]
  );
  const maxSeq = rows[0]?.max_seq || 0;
  const seq = String(maxSeq + 1).padStart(3, '0');

  // 校验码: (前缀 + 流水号)各位数字之和 mod 97
  const base = prefix + seq;
  let sum = 0;
  for (const ch of base) {
    sum += parseInt(ch, 10);
  }
  const checkCode = String(sum % 97).padStart(2, '0');
  return base + checkCode;
}

// POST /api/prescriptions — create prescription (doctor only)
router.post('/', requireRole('doctor', 'admin'), async (req: Request, res: Response) => {
  const conn = await pool.getConnection();
  try {
    const { patient_id, diagnosis, note, items, prescription_type, payment_type, medical_record_no, department, bed_no } = req.body;

    if (!patient_id || !diagnosis || !items || !Array.isArray(items) || items.length === 0) {
      res.status(400).json({ error: '请填写完整的处方信息（病人、诊断、药品）' });
      return;
    }

    // 每张处方不得超过五种药品
    if (items.length > 5) {
      res.status(400).json({ error: '每张处方不得超过5种药品' });
      return;
    }

    // 计算药品总金额
    let totalAmount = 0;
    for (const item of items) {
      const [medRows] = await conn.query<any[]>('SELECT price FROM medicines WHERE id = ?', [item.medicine_id]);
      if (medRows.length > 0) {
        totalAmount += Number(medRows[0].price) * (item.quantity || 1);
      }
    }

    const prescriptionType = prescription_type || '普通';
    await conn.beginTransaction();
    const prescriptionCode = await generatePrescriptionCode(prescriptionType, conn);

    const [prescResult] = await conn.query(
      `INSERT INTO prescriptions
       (patient_id, doctor_id, diagnosis, note, status, prescription_type, payment_type, medical_record_no, department, bed_no, total_amount, prescription_code)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [patient_id, req.user!.id, diagnosis, note || null, 'pending',
       prescriptionType, payment_type || '医保', medical_record_no || null,
       department || null, bed_no || null, totalAmount, prescriptionCode]
    );
    const prescriptionId = (prescResult as any).insertId;

    for (const item of items) {
      await conn.query(
        `INSERT INTO prescription_items (prescription_id, medicine_id, drug_form, dosage, usage_method, frequency, days, quantity, note)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        [
          prescriptionId, item.medicine_id, item.drug_form || null,
          item.dosage, item.usage_method || '口服', item.frequency || '每日3次',
          item.days || 3, item.quantity || 1, item.note || null,
        ]
      );
    }

    await conn.commit();
    res.status(201).json({ id: prescriptionId, prescription_code: prescriptionCode, message: '处方已提交，等待药师审核' });
  } catch (err: any) {
    await conn.rollback();
    res.status(500).json({ error: '服务器错误: ' + err.message });
  } finally {
    conn.release();
  }
});

// GET /api/prescriptions — list (filtered by role)
router.get('/', async (req: Request, res: Response) => {
  try {
    const page = parseInt(req.query.page as string) || 1;
    const pageSize = parseInt(req.query.pageSize as string) || 10;
    const status = req.query.status as string;
    const prescriptionType = req.query.prescription_type as string;
    const offset = (page - 1) * pageSize;
    const user = req.user!;

    const conditions: string[] = [];
    const params: any[] = [];

    // Doctor sees their own prescriptions; pharmacist/admin sees all
    if (user.role === 'doctor') {
      conditions.push('p.doctor_id = ?');
      params.push(user.id);
    }

    if (status) {
      conditions.push('p.status = ?');
      params.push(status);
    }

    if (prescriptionType) {
      conditions.push('p.prescription_type = ?');
      params.push(prescriptionType);
    }

    const whereClause = conditions.length > 0 ? 'WHERE ' + conditions.join(' AND ') : '';

    const [countRows] = await pool.query<any[]>(
      `SELECT COUNT(*) as total FROM prescriptions p ${whereClause}`,
      params.length ? params : undefined
    );
    const total = countRows[0]?.total || 0;

    const listParams = [...params, pageSize, offset];
    const [list] = await pool.query(
      `SELECT p.*, pt.name as patient_name, u.real_name as doctor_name
       FROM prescriptions p
       LEFT JOIN patients pt ON p.patient_id = pt.id
       LEFT JOIN users u ON p.doctor_id = u.id
       ${whereClause}
       ORDER BY p.created_at DESC
       LIMIT ? OFFSET ?`,
      listParams
    );

    res.json({ total, page, pageSize, list });
  } catch (err: any) {
    res.status(500).json({ error: '服务器错误: ' + err.message });
  }
});

// GET /api/prescriptions/:id — detail with items
router.get('/:id', async (req: Request, res: Response) => {
  try {
    const id = parseInt(req.params.id);

    const [prescriptions] = await pool.query<any[]>(
      `SELECT p.*, pt.name as patient_name, pt.gender as patient_gender, pt.age as patient_age,
              u.real_name as doctor_name
       FROM prescriptions p
       LEFT JOIN patients pt ON p.patient_id = pt.id
       LEFT JOIN users u ON p.doctor_id = u.id
       WHERE p.id = ?`,
      [id]
    );

    if (prescriptions.length === 0) {
      res.status(404).json({ error: '处方不存在' });
      return;
    }

    const prescription = prescriptions[0];

    // Get items
    const [items] = await pool.query(
      `SELECT pi.*, m.name as medicine_name, m.specification, m.manufacturer, m.unit
       FROM prescription_items pi
       LEFT JOIN medicines m ON pi.medicine_id = m.id
       WHERE pi.prescription_id = ?`,
      [id]
    );

    res.json({ ...prescription, items });
  } catch (err: any) {
    res.status(500).json({ error: '服务器错误: ' + err.message });
  }
});

// PUT /api/prescriptions/:id/review — pharmacist review
router.put('/:id/review', requireRole('pharmacist', 'admin'), async (req: Request, res: Response) => {
  try {
    const id = parseInt(req.params.id);
    const { status, note } = req.body;

    if (!['approved', 'rejected'].includes(status)) {
      res.status(400).json({ error: '审核状态只能是 approved 或 rejected' });
      return;
    }

    // Check prescription exists and is pending
    const [checkRows] = await pool.query<any[]>(
      'SELECT status FROM prescriptions WHERE id = ?',
      [id]
    );

    if (checkRows.length === 0) {
      res.status(404).json({ error: '处方不存在' });
      return;
    }

    if (checkRows[0].status !== 'pending') {
      res.status(400).json({ error: '该处方已被审核，无法重复操作' });
      return;
    }

    await pool.query(
      'UPDATE prescriptions SET status=?, pharmacist_review_id=?, reviewed_at=NOW(), note=COALESCE(NULLIF(?, \'\'), note) WHERE id=?',
      [status, req.user!.id, note || null, id]
    );

    const msg = status === 'approved' ? '处方审核已通过' : '处方已被驳回';
    res.json({ message: msg });
  } catch (err: any) {
    res.status(500).json({ error: '服务器错误: ' + err.message });
  }
});

// PUT /api/prescriptions/:id/dispense — confirm dispensing
router.put('/:id/dispense', requireRole('pharmacist', 'admin'), async (req: Request, res: Response) => {
  try {
    const id = parseInt(req.params.id);

    const [checkRows] = await pool.query<any[]>(
      'SELECT status FROM prescriptions WHERE id = ?',
      [id]
    );

    if (checkRows.length === 0) {
      res.status(404).json({ error: '处方不存在' });
      return;
    }

    if (checkRows[0].status !== 'approved') {
      res.status(400).json({ error: '只有审核通过的处方才能发药' });
      return;
    }

    await pool.query(
      'UPDATE prescriptions SET status=\'dispensed\', pharmacist_dispense_id=?, dispensed_at=NOW() WHERE id=?',
      [req.user!.id, id]
    );

    res.json({ message: '药品已发放' });
  } catch (err: any) {
    res.status(500).json({ error: '服务器错误: ' + err.message });
  }
});

// DELETE /api/prescriptions/:id — delete prescription and its items
router.delete('/:id', async (req: Request, res: Response) => {
  const conn = await pool.getConnection();
  try {
    const id = parseInt(req.params.id);

    const [checkRows] = await conn.query<any[]>(
      'SELECT id FROM prescriptions WHERE id = ?', [id]
    );

    if (checkRows.length === 0) {
      res.status(404).json({ error: '处方不存在' });
      return;
    }

    await conn.beginTransaction();
    await conn.query('DELETE FROM prescription_items WHERE prescription_id = ?', [id]);
    await conn.query('DELETE FROM prescriptions WHERE id = ?', [id]);
    await conn.commit();

    res.json({ message: '处方已删除' });
  } catch (err: any) {
    await conn.rollback();
    res.status(500).json({ error: '服务器错误: ' + err.message });
  } finally {
    conn.release();
  }
});

export default router;
