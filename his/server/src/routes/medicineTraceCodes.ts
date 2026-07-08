import { Router, Request, Response } from 'express';
import pool from '../db';
import { authMiddleware } from '../middleware/auth';

const router = Router();
router.use(authMiddleware);

// GET /api/medicine-trace-codes — list with pagination, filterable by medicine_id
router.get('/', async (req: Request, res: Response) => {
  try {
    const page = parseInt(req.query.page as string) || 1;
    const pageSize = parseInt(req.query.pageSize as string) || 10;
    const medicineId = parseInt(req.query.medicine_id as string);
    const offset = (page - 1) * pageSize;

    let countSql = 'SELECT COUNT(*) as total FROM medicine_trace_codes tc';
    let listSql = `SELECT tc.*, u1.real_name AS scan1_user_name, u2.real_name AS scan2_user_name, u3.real_name AS scan3_user_name
      FROM medicine_trace_codes tc
      LEFT JOIN users u1 ON tc.scan1_user_id = u1.id
      LEFT JOIN users u2 ON tc.scan2_user_id = u2.id
      LEFT JOIN users u3 ON tc.scan3_user_id = u3.id`;
    const params: any[] = [];

    if (!isNaN(medicineId)) {
      const where = ' WHERE tc.medicine_id = ?';
      countSql += where;
      listSql += where;
      params.push(medicineId);
    }

    listSql += ' ORDER BY COALESCE(tc.scan3_time, tc.scan2_time, tc.scan1_time, tc.created_at) DESC, tc.id ASC LIMIT ? OFFSET ?';

    const [countRows] = await pool.query<any[]>(countSql, params);
    const total = (countRows[0] as any)?.total || 0;

    const listParams = [...params, pageSize, offset];
    const [rows] = await pool.query(listSql, listParams);

    res.json({ total, page, pageSize, list: rows });
  } catch (err: any) {
    res.status(500).json({ error: '服务器错误: ' + err.message });
  }
});

// 药品追溯码前缀映射（硬编码兜底，数据库表优先）
const MEDICINE_PREFIX_MAP: Record<string, string> = {
  '米索前列醇片': '8422747',
  '阿莫西林胶囊': '1730604',
  '康恩贝肠炎宁片': '8410131',
  '肠炎宁片': '8410131',
  '苏黄止咳胶囊': '8390696',
  '去痛片': '8341039',
  '奥美拉唑肠溶胶囊': '8169438',
  '奥美拉唑': '8169438',
  '蒙脱石散': '8425186',
  '元和正胃片': '8377024',
  '氨苄西林胶囊': '8340166',
};

// 从数据库查询所有前缀（优先），表不存在或为空时回退到硬编码
const getPrefixMap = async (conn: any): Promise<Map<number, string>> => {
  try {
    const [rows] = await conn.query<any[]>('SELECT medicine_id, prefix FROM medicine_trace_prefixes');
    if (rows.length > 0) {
      return new Map(rows.map((r: any) => [r.medicine_id, r.prefix]));
    }
  } catch (_e) {
    // 表可能还没创建，回退到硬编码
  }
  // 回退：按药品名匹配硬编码前缀
  const [medicines] = await conn.query<any[]>('SELECT id, name FROM medicines');
  const map = new Map<number, string>();
  for (const m of medicines) {
    if (MEDICINE_PREFIX_MAP[m.name]) {
      map.set(m.id, MEDICINE_PREFIX_MAP[m.name]);
    }
  }
  return map;
};

const randomTraceCode = (prefix?: string): string => {
  const chars = '0123456789';
  if (prefix) {
    // 前缀7位 + 随机13位 = 20位追溯码
    let code = prefix;
    for (let i = 0; i < 13; i++) {
      code += chars[Math.floor(Math.random() * chars.length)];
    }
    return code;
  }
  // 无前缀时全部随机20位
  let code = '';
  for (let i = 0; i < 20; i++) {
    code += chars[Math.floor(Math.random() * chars.length)];
  }
  return code;
};

// POST /api/medicine-trace-codes — create user's code, then auto-generate remaining based on stock
router.post('/', async (req: Request, res: Response) => {
  try {
    const { medicine_id, trace_code } = req.body;
    if (!medicine_id || !trace_code) {
      res.status(400).json({ error: 'medicine_id 和 trace_code 为必填项' });
      return;
    }

    // Get medicine stock and name (for prefix lookup)
    const [medRows] = await pool.query<any[]>('SELECT name, stock FROM medicines WHERE id = ?', [medicine_id]);
    if (medRows.length === 0) {
      res.status(404).json({ error: '药品不存在' });
      return;
    }
    const stock = medRows[0].stock;

    // 获取前缀映射表
    const prefixMap = await getPrefixMap(pool);
    const prefix = prefixMap.get(medicine_id);

    // Count existing trace codes for this medicine
    const [countRows] = await pool.query<any[]>('SELECT COUNT(*) as cnt FROM medicine_trace_codes WHERE medicine_id = ?', [medicine_id]);
    const existingCount = countRows[0].cnt;

    // Insert user's trace code first
    const [result] = await pool.query(
      'INSERT INTO medicine_trace_codes (medicine_id, trace_code) VALUES (?, ?)',
      [medicine_id, trace_code.trim()]
    );
    const userInsertId = (result as any).insertId;

    // Auto-generate remaining codes if stock > existingCount + 1
    const needCount = stock - existingCount - 1;
    const generatedCodes: string[] = [];
    if (needCount > 0) {
      const values: any[] = [];
      const placeholders: string[] = [];
      for (let i = 0; i < needCount; i++) {
        const code = randomTraceCode(prefix);
        placeholders.push('(?, ?)');
        values.push(medicine_id, code);
        generatedCodes.push(code);
      }
      await pool.query(`INSERT INTO medicine_trace_codes (medicine_id, trace_code) VALUES ${placeholders.join(', ')}`, values);
    }

    res.status(201).json({
      id: userInsertId,
      message: `已添加追溯码，自动生成 ${generatedCodes.length} 条`,
      generatedCount: generatedCodes.length,
    });
  } catch (err: any) {
    if (err.code === 'ER_DUP_ENTRY') {
      res.status(409).json({ error: '该追溯码已被使用' });
      return;
    }
    res.status(500).json({ error: '服务器错误: ' + err.message });
  }
});

// POST /api/medicine-trace-codes/generate-all — batch generate for all medicines
router.post('/generate-all', async (_req: Request, res: Response) => {
  try {
    // Get all medicines with stock > 0
    const [medicines] = await pool.query<any[]>('SELECT id, name, stock FROM medicines WHERE stock > 0');

    // 获取前缀映射表
    const prefixMap = await getPrefixMap(pool);

    let totalGenerated = 0;
    const results: string[] = [];

    for (const med of medicines) {
      // Count existing trace codes
      const [countRows] = await pool.query<any[]>('SELECT COUNT(*) as cnt FROM medicine_trace_codes WHERE medicine_id = ?', [med.id]);
      const existingCount = countRows[0].cnt;
      const needCount = med.stock - existingCount;

      if (needCount > 0) {
        const prefix = prefixMap.get(med.id);
        const values: any[] = [];
        const placeholders: string[] = [];
        for (let i = 0; i < needCount; i++) {
          const code = randomTraceCode(prefix);
          placeholders.push('(?, ?)');
          values.push(med.id, code);
        }
        await pool.query(`INSERT INTO medicine_trace_codes (medicine_id, trace_code) VALUES ${placeholders.join(', ')}`, values);
        totalGenerated += needCount;
        results.push(`${med.name}: 已生成 ${needCount} 条`);
      }
    }

    res.json({
      message: `批量生成完成，共生成 ${totalGenerated} 条追溯码`,
      totalGenerated,
      details: results,
    });
  } catch (err: any) {
    res.status(500).json({ error: '服务器错误: ' + err.message });
  }
});

// POST /api/medicine-trace-codes/regenerate-all — 清空全部追溯码并重新生成（使用药品前缀）
router.post('/regenerate-all', async (_req: Request, res: Response) => {
  const conn = await pool.getConnection();
  try {
    await conn.beginTransaction();

    // 1. 清空全部追溯码
    const [deleteResult] = await conn.query<any>('DELETE FROM medicine_trace_codes');
    const deletedCount = (deleteResult as any)?.affectedRows || 0;

    // 2. 获取所有库存 > 0 的药品
    const [medicines] = await conn.query<any[]>('SELECT id, name, stock FROM medicines WHERE stock > 0');

    // 获取前缀映射表（使用当前连接以支持事务）
    const prefixMap = await getPrefixMap(conn);

    let totalGenerated = 0;
    const details: string[] = [];

    for (const med of medicines) {
      const prefix = prefixMap.get(med.id);
      const values: any[] = [];
      const placeholders: string[] = [];

      for (let i = 0; i < med.stock; i++) {
        const code = randomTraceCode(prefix);
        placeholders.push('(?, ?)');
        values.push(med.id, code);
      }

      if (placeholders.length > 0) {
        await conn.query(
          `INSERT INTO medicine_trace_codes (medicine_id, trace_code) VALUES ${placeholders.join(', ')}`,
          values
        );
        totalGenerated += med.stock;
        details.push(`${med.name}: 生成 ${med.stock} 条 (前缀: ${prefix || '无'})`);
      }
    }

    await conn.commit();

    res.json({
      message: `已清空 ${deletedCount} 条旧追溯码，重新生成 ${totalGenerated} 条新追溯码`,
      deletedCount,
      totalGenerated,
      details,
    });
  } catch (err: any) {
    await conn.rollback();
    res.status(500).json({ error: '操作失败，已回滚: ' + err.message });
  } finally {
    conn.release();
  }
});

// PUT /api/medicine-trace-codes/:id — update
router.put('/:id', async (req: Request, res: Response) => {
  try {
    const id = parseInt(req.params.id);
    const { trace_code } = req.body;

    if (!trace_code) {
      res.status(400).json({ error: '追溯码为必填项' });
      return;
    }

    const [checkRows] = await pool.query<any[]>(
      'SELECT id FROM medicine_trace_codes WHERE id = ?', [id]
    );
    if (checkRows.length === 0) {
      res.status(404).json({ error: '追溯码不存在' });
      return;
    }

    await pool.query(
      'UPDATE medicine_trace_codes SET trace_code = ? WHERE id = ?',
      [trace_code.trim(), id]
    );

    res.json({ message: '追溯码已更新' });
  } catch (err: any) {
    if (err.code === 'ER_DUP_ENTRY') {
      res.status(409).json({ error: '该追溯码已被使用' });
      return;
    }
    res.status(500).json({ error: '服务器错误: ' + err.message });
  }
});

// DELETE /api/medicine-trace-codes/:id — delete
router.delete('/:id', async (req: Request, res: Response) => {
  try {
    const id = parseInt(req.params.id);

    const [checkRows] = await pool.query<any[]>(
      'SELECT id FROM medicine_trace_codes WHERE id = ?', [id]
    );
    if (checkRows.length === 0) {
      res.status(404).json({ error: '追溯码不存在' });
      return;
    }

    await pool.query('DELETE FROM medicine_trace_codes WHERE id = ?', [id]);
    res.json({ message: '追溯码已删除' });
  } catch (err: any) {
    res.status(500).json({ error: '服务器错误: ' + err.message });
  }
});

// PUT /api/medicine-trace-codes/:id/scan — advance scan status
router.put('/:id/scan', async (req: Request, res: Response) => {
  try {
    const id = parseInt(req.params.id);
    const userId = (req as any).user?.id;
    const prescriptionId = req.body.prescription_id ? parseInt(req.body.prescription_id) : null;

    const [rows] = await pool.query<any[]>(
      'SELECT * FROM medicine_trace_codes WHERE id = ?', [id]
    );
    if (rows.length === 0) {
      res.status(404).json({ error: '追溯码不存在' });
      return;
    }

    const record = rows[0];
    const currentStatus: string = record.status;

    let updateSql: string;
    const updateParams: any[] = [];

    if (currentStatus === 'pending') {
      updateSql = 'UPDATE medicine_trace_codes SET status = ?, scan1_time = NOW(), scan1_user_id = ?, prescription_id = COALESCE(?, prescription_id) WHERE id = ?';
      updateParams.push('scanned_identify', userId, prescriptionId, id);
    } else if (currentStatus === 'scanned_identify') {
      updateSql = 'UPDATE medicine_trace_codes SET status = ?, scan2_time = NOW(), scan2_user_id = ?, prescription_id = COALESCE(?, prescription_id) WHERE id = ?';
      updateParams.push('scanned_outbound', userId, prescriptionId, id);
    } else if (currentStatus === 'scanned_outbound') {
      updateSql = 'UPDATE medicine_trace_codes SET status = ?, scan3_time = NOW(), scan3_user_id = ?, prescription_id = COALESCE(?, prescription_id) WHERE id = ?';
      updateParams.push('scanned_confirm', userId, prescriptionId, id);
    } else {
      res.status(400).json({ error: '该追溯码已完成全部扫描' });
      return;
    }

    await pool.query(updateSql, updateParams);

    // Return updated record with operator names
    const [updated] = await pool.query<any[]>(
      `SELECT tc.*, u1.real_name AS scan1_user_name, u2.real_name AS scan2_user_name, u3.real_name AS scan3_user_name
       FROM medicine_trace_codes tc
       LEFT JOIN users u1 ON tc.scan1_user_id = u1.id
       LEFT JOIN users u2 ON tc.scan2_user_id = u2.id
       LEFT JOIN users u3 ON tc.scan3_user_id = u3.id
       WHERE tc.id = ?`, [id]
    );

    res.json(updated[0]);
  } catch (err: any) {
    res.status(500).json({ error: '服务器错误: ' + err.message });
  }
});

// PUT /api/medicine-trace-codes/:id/unscan — revoke scan (go back one step)
router.put('/:id/unscan', async (req: Request, res: Response) => {
  try {
    const id = parseInt(req.params.id);

    const [rows] = await pool.query<any[]>(
      'SELECT * FROM medicine_trace_codes WHERE id = ?', [id]
    );
    if (rows.length === 0) {
      res.status(404).json({ error: '追溯码不存在' });
      return;
    }

    const record = rows[0];
    const currentStatus: string = record.status;

    let updateSql: string;
    const updateParams: any[] = [];

    if (currentStatus === 'scanned_confirm') {
      updateSql = 'UPDATE medicine_trace_codes SET status = ?, scan3_time = NULL, scan3_user_id = NULL WHERE id = ?';
      updateParams.push('scanned_outbound', id);
    } else if (currentStatus === 'scanned_outbound') {
      updateSql = 'UPDATE medicine_trace_codes SET status = ?, scan2_time = NULL, scan2_user_id = NULL WHERE id = ?';
      updateParams.push('scanned_identify', id);
    } else if (currentStatus === 'scanned_identify') {
      updateSql = 'UPDATE medicine_trace_codes SET status = ?, scan1_time = NULL, scan1_user_id = NULL WHERE id = ?';
      updateParams.push('pending', id);
    } else {
      res.status(400).json({ error: '该追溯码尚未扫描，无法撤回' });
      return;
    }

    await pool.query(updateSql, updateParams);

    // Return updated record
    const [updated] = await pool.query<any[]>(
      `SELECT tc.*, u1.real_name AS scan1_user_name, u2.real_name AS scan2_user_name, u3.real_name AS scan3_user_name
       FROM medicine_trace_codes tc
       LEFT JOIN users u1 ON tc.scan1_user_id = u1.id
       LEFT JOIN users u2 ON tc.scan2_user_id = u2.id
       LEFT JOIN users u3 ON tc.scan3_user_id = u3.id
       WHERE tc.id = ?`, [id]
    );

    res.json(updated[0]);
  } catch (err: any) {
    res.status(500).json({ error: '服务器错误: ' + err.message });
  }
});

// POST /api/medicine-trace-codes/scan-by-code — scan by trace_code string (for mobile scanner)
router.post('/scan-by-code', async (req: Request, res: Response) => {
  try {
    const { trace_code, prescription_id } = req.body;
    if (!trace_code) {
      res.status(400).json({ error: '追溯码不能为空' });
      return;
    }

    const prescriptionId = prescription_id ? parseInt(prescription_id) : null;

    // Find the trace code record
    const [rows] = await pool.query<any[]>(
      'SELECT * FROM medicine_trace_codes WHERE trace_code = ?', [trace_code.trim()]
    );
    if (rows.length === 0) {
      res.status(404).json({ error: '追溯码未找到' });
      return;
    }

    const record = rows[0];
    const userId = (req as any).user?.id;

    // Advance scan status
    let updateSql: string;
    const updateParams: any[] = [];
    let actionName: string;

    if (record.status === 'pending') {
      updateSql = 'UPDATE medicine_trace_codes SET status = ?, scan1_time = NOW(), scan1_user_id = ?, prescription_id = COALESCE(?, prescription_id) WHERE id = ?';
      updateParams.push('scanned_identify', userId, prescriptionId, record.id);
      actionName = '识别';
    } else if (record.status === 'scanned_identify') {
      updateSql = 'UPDATE medicine_trace_codes SET status = ?, scan2_time = NOW(), scan2_user_id = ?, prescription_id = COALESCE(?, prescription_id) WHERE id = ?';
      updateParams.push('scanned_outbound', userId, prescriptionId, record.id);
      actionName = '出库';
    } else if (record.status === 'scanned_outbound') {
      updateSql = 'UPDATE medicine_trace_codes SET status = ?, scan3_time = NOW(), scan3_user_id = ?, prescription_id = COALESCE(?, prescription_id) WHERE id = ?';
      updateParams.push('scanned_confirm', userId, prescriptionId, record.id);
      actionName = '确认';
    } else {
      res.json({ message: '该追溯码已完成全部扫描', status: record.status, completed: true });
      return;
    }

    await pool.query(updateSql, updateParams);

    // Return updated record with medicine info
    const [updated] = await pool.query<any[]>(
      `SELECT tc.*, m.name AS medicine_name, m.specification, m.manufacturer,
        u1.real_name AS scan1_user_name, u2.real_name AS scan2_user_name, u3.real_name AS scan3_user_name
       FROM medicine_trace_codes tc
       JOIN medicines m ON tc.medicine_id = m.id
       LEFT JOIN users u1 ON tc.scan1_user_id = u1.id
       LEFT JOIN users u2 ON tc.scan2_user_id = u2.id
       LEFT JOIN users u3 ON tc.scan3_user_id = u3.id
       WHERE tc.id = ?`, [record.id]
    );

    res.json({ ...updated[0], action: actionName, completed: actionName === '确认' });
  } catch (err: any) {
    res.status(500).json({ error: '服务器错误: ' + err.message });
  }
});

export default router;
