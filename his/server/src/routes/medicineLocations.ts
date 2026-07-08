import { Router, Request, Response } from 'express';
import pool from '../db';
import { authMiddleware } from '../middleware/auth';

const router = Router();
router.use(authMiddleware);

// GET /api/medicine-locations — list all with optional search
router.get('/', async (req: Request, res: Response) => {
  try {
    const page = parseInt(req.query.page as string) || 1;
    const pageSize = parseInt(req.query.pageSize as string) || 50;
    const keyword = (req.query.keyword as string) || '';
    const offset = (page - 1) * pageSize;

    let countSql = 'SELECT COUNT(*) as total FROM medicine_locations';
    let listSql = `
      SELECT ml.*, m.specification, m.manufacturer, p.prefix AS trace_code_prefix
      FROM medicine_locations ml
      LEFT JOIN medicines m ON ml.medicine_id = m.id
      LEFT JOIN medicine_trace_prefixes p ON ml.medicine_id = p.medicine_id
    `;
    const params: any[] = [];

    if (keyword) {
      const where = ' WHERE ml.medicine_name LIKE ?';
      countSql += where;
      listSql += where;
      params.push(`%${keyword}%`);
    }

    listSql += ' ORDER BY ml.id ASC LIMIT ? OFFSET ?';

    const [countRows] = await pool.query<any[]>(countSql, params.length ? params : undefined);
    const total = countRows[0]?.total || 0;

    const listParams = [...params, pageSize, offset];
    const [locations] = await pool.query(listSql, listParams);

    res.json({ total, page, pageSize, list: locations });
  } catch (err: any) {
    res.status(500).json({ error: '服务器错误: ' + err.message });
  }
});

// GET /api/medicine-locations/:id — single location
router.get('/:id', async (req: Request, res: Response) => {
  try {
    const id = parseInt(req.params.id);

    const [rows] = await pool.query<any[]>(
      `SELECT ml.*, m.specification, m.manufacturer, p.prefix AS trace_code_prefix
       FROM medicine_locations ml
       LEFT JOIN medicines m ON ml.medicine_id = m.id
       LEFT JOIN medicine_trace_prefixes p ON ml.medicine_id = p.medicine_id
       WHERE ml.id = ?`,
      [id]
    );

    if (rows.length === 0) {
      res.status(404).json({ error: '药品位置信息不存在' });
      return;
    }

    res.json(rows[0]);
  } catch (err: any) {
    res.status(500).json({ error: '服务器错误: ' + err.message });
  }
});

// POST /api/medicine-locations — create
router.post('/', async (req: Request, res: Response) => {
  try {
    const { medicine_id, medicine_name, x, y, z } = req.body;

    if (!medicine_id || !medicine_name) {
      res.status(400).json({ error: '药品ID和药品名称为必填项' });
      return;
    }

    const [result] = await pool.query(
      'INSERT INTO medicine_locations (medicine_id, medicine_name, x, y, z) VALUES (?, ?, ?, ?, ?)',
      [medicine_id, medicine_name, x ?? 0, y ?? 0, z ?? 0]
    );

    res.status(201).json({ id: (result as any).insertId, message: '药品位置信息已保存' });
  } catch (err: any) {
    res.status(500).json({ error: '服务器错误: ' + err.message });
  }
});

// PUT /api/medicine-locations/:id — update
router.put('/:id', async (req: Request, res: Response) => {
  try {
    const id = parseInt(req.params.id);
    const { medicine_id, medicine_name, x, y, z } = req.body;

    await pool.query(
      'UPDATE medicine_locations SET medicine_id=?, medicine_name=?, x=?, y=?, z=? WHERE id=?',
      [medicine_id, medicine_name, x ?? 0, y ?? 0, z ?? 0, id]
    );

    res.json({ message: '药品位置信息已更新' });
  } catch (err: any) {
    res.status(500).json({ error: '服务器错误: ' + err.message });
  }
});

// DELETE /api/medicine-locations/:id — delete
router.delete('/:id', async (req: Request, res: Response) => {
  try {
    const id = parseInt(req.params.id);

    const [checkRows] = await pool.query<any[]>(
      'SELECT id FROM medicine_locations WHERE id = ?',
      [id]
    );

    if (checkRows.length === 0) {
      res.status(404).json({ error: '药品位置信息不存在' });
      return;
    }

    await pool.query('DELETE FROM medicine_locations WHERE id = ?', [id]);

    res.json({ message: '药品位置信息已删除' });
  } catch (err: any) {
    res.status(500).json({ error: '服务器错误: ' + err.message });
  }
});

export default router;
