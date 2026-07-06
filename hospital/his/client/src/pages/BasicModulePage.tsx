import { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import ModuleIcon, { type ModuleIconName } from '../components/ModuleIcon';
import { showToast } from '../components/Toast';
import { medicineApi, patientApi, prescriptionApi } from '../services/api';
import type { Medicine, Prescription } from '../types';
import { STATUS_LABELS } from '../types';
import { formatDateTime } from '../utils/date';

type BasicModuleKind =
  | 'dispense'
  | 'reports'
  | 'medicineSettings'
  | 'writeoff'
  | 'operationLog'
  | 'medicineDown'
  | 'restock'
  | 'inventory';

interface Props {
  kind: BasicModuleKind;
  title: string;
  icon: ModuleIconName;
}

export default function BasicModulePage({ kind, title, icon }: Props) {
  const [medicines, setMedicines] = useState<Medicine[]>([]);
  const [prescriptions, setPrescriptions] = useState<Prescription[]>([]);
  const [patientTotal, setPatientTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [keyword, setKeyword] = useState('');
  const [busyId, setBusyId] = useState<number | null>(null);
  const [prefixDrafts, setPrefixDrafts] = useState<Record<number, string>>({});
  const [restockDrafts, setRestockDrafts] = useState<Record<number, string>>({});
  const [writeoffIds, setWriteoffIds] = useState<Set<number>>(new Set());
  const [downIds, setDownIds] = useState<Set<number>>(new Set());

  const load = async () => {
    setLoading(true);
    try {
      const [medicineRes, prescriptionRes, patientRes] = await Promise.all([
        medicineApi.list({ page: 1, pageSize: 200, keyword }),
        prescriptionApi.list({ page: 1, pageSize: 200 }),
        patientApi.list({ page: 1, pageSize: 1 }),
      ]);
      setMedicines(medicineRes.list);
      setPrescriptions(prescriptionRes.list);
      setPatientTotal(patientRes.total);
      setPrefixDrafts(Object.fromEntries(medicineRes.list.map((m) => [m.id, m.trace_code_prefix || ''])));
    } catch (err) {
      console.error(err);
      showToast('数据加载失败', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const filteredMedicines = useMemo(() => {
    const key = keyword.trim().toLowerCase();
    if (!key) return medicines;
    return medicines.filter((m) =>
      [m.name, m.generic_name, m.manufacturer, m.specification].some((v) => String(v || '').toLowerCase().includes(key))
    );
  }, [keyword, medicines]);

  const pendingPrescriptions = prescriptions.filter((p) => p.status === 'pending');
  const approvedPrescriptions = prescriptions.filter((p) => p.status === 'approved');
  const dispensedPrescriptions = prescriptions.filter((p) => p.status === 'dispensed');
  const lowStockMedicines = medicines.filter((m) => Number(m.stock) <= 20);
  const totalStock = medicines.reduce((sum, m) => sum + Number(m.stock || 0), 0);

  const updateMedicine = async (medicine: Medicine, patch: Partial<Medicine>) => {
    setBusyId(medicine.id);
    try {
      await medicineApi.update(medicine.id, {
        name: patch.name ?? medicine.name,
        generic_name: patch.generic_name ?? medicine.generic_name ?? '',
        specification: patch.specification ?? medicine.specification ?? '',
        drug_form: patch.drug_form ?? medicine.drug_form ?? '',
        manufacturer: patch.manufacturer ?? medicine.manufacturer ?? '',
        unit: patch.unit ?? medicine.unit,
        price: patch.price ?? medicine.price,
        stock: patch.stock ?? medicine.stock,
        category: patch.category ?? medicine.category,
        is_narcotic: Boolean(patch.is_narcotic ?? medicine.is_narcotic),
        image_url: patch.image_url ?? medicine.image_url ?? '',
        trace_code_prefix: patch.trace_code_prefix ?? medicine.trace_code_prefix ?? '',
      });
      await load();
      showToast('保存成功', 'success');
    } catch (err: any) {
      showToast(err.response?.data?.error || '保存失败', 'error');
    } finally {
      setBusyId(null);
    }
  };

  const dispense = async (prescription: Prescription) => {
    setBusyId(prescription.id);
    try {
      const res = await prescriptionApi.dispense(prescription.id);
      showToast(res.message || '已确认发药', 'success');
      await load();
    } catch (err: any) {
      showToast(err.response?.data?.error || '发药失败', 'error');
    } finally {
      setBusyId(null);
    }
  };

  const savePrefix = async (medicine: Medicine) => {
    const prefix = (prefixDrafts[medicine.id] || '').trim();
    if (prefix && !/^\d{7}$/.test(prefix)) {
      showToast('前缀必须是 7 位数字', 'error');
      return;
    }
    await updateMedicine(medicine, { trace_code_prefix: prefix });
  };

  const restock = async (medicine: Medicine) => {
    const amount = Number(restockDrafts[medicine.id] || 0);
    if (!Number.isFinite(amount) || amount <= 0) {
      showToast('请输入大于 0 的补药数量', 'error');
      return;
    }
    await updateMedicine(medicine, { stock: Number(medicine.stock || 0) + amount });
    setRestockDrafts((prev) => ({ ...prev, [medicine.id]: '' }));
  };

  const renderContent = () => {
    if (loading) return <div className="loading">加载中...</div>;

    if (kind === 'dispense') {
      return (
        <BasicTable headers={['处方编号', '病人', '诊断', '状态', '时间', '操作']}>
          {approvedPrescriptions.map((p) => (
            <tr key={p.id}>
              <td><strong>{p.prescription_code || `#${p.id}`}</strong></td>
              <td>{p.patient_name || '-'}</td>
              <td>{p.diagnosis}</td>
              <td>{STATUS_LABELS[p.status]}</td>
              <td>{formatDateTime(p.created_at)}</td>
              <td><button className="glass-btn glass-btn--primary glass-btn--sm" disabled={busyId === p.id} onClick={() => dispense(p)}>确认发药</button></td>
            </tr>
          ))}
        </BasicTable>
      );
    }

    if (kind === 'reports') {
      return (
        <>
          <div className="module-basic-stats">
            <Stat label="病人总数" value={patientTotal} />
            <Stat label="药品种类" value={medicines.length} />
            <Stat label="库存总量" value={totalStock} />
            <Stat label="待审核处方" value={pendingPrescriptions.length} />
          </div>
          <BasicTable headers={['项目', '数量']}>
            <tr><td>待发药处方</td><td>{approvedPrescriptions.length}</td></tr>
            <tr><td>已发药处方</td><td>{dispensedPrescriptions.length}</td></tr>
            <tr><td>低库存药品</td><td>{lowStockMedicines.length}</td></tr>
          </BasicTable>
        </>
      );
    }

    if (kind === 'medicineSettings') {
      return (
        <BasicTable headers={['药品', '规格', '追溯码前缀', '操作']}>
          {filteredMedicines.map((m) => (
            <tr key={m.id}>
              <td><strong>{m.name}</strong></td>
              <td>{m.specification || '-'}</td>
              <td><input className="glass-input module-basic-input" value={prefixDrafts[m.id] || ''} onChange={(e) => setPrefixDrafts((prev) => ({ ...prev, [m.id]: e.target.value.replace(/\D/g, '').slice(0, 7) }))} placeholder="7位数字" /></td>
              <td><button className="glass-btn glass-btn--primary glass-btn--sm" disabled={busyId === m.id} onClick={() => savePrefix(m)}>保存</button></td>
            </tr>
          ))}
        </BasicTable>
      );
    }

    if (kind === 'writeoff') {
      return (
        <BasicTable headers={['处方编号', '病人', '金额', '状态', '销账']}>
          {dispensedPrescriptions.map((p) => (
            <tr key={p.id}>
              <td><strong>{p.prescription_code || `#${p.id}`}</strong></td>
              <td>{p.patient_name || '-'}</td>
              <td>¥{Number(p.total_amount || 0).toFixed(2)}</td>
              <td>{writeoffIds.has(p.id) ? '已销账' : '待销账'}</td>
              <td><button className="glass-btn glass-btn--primary glass-btn--sm" disabled={writeoffIds.has(p.id)} onClick={() => setWriteoffIds((prev) => new Set(prev).add(p.id))}>确认销账</button></td>
            </tr>
          ))}
        </BasicTable>
      );
    }

    if (kind === 'operationLog') {
      const rows = prescriptions.slice(0, 40).map((p) => ({
        id: p.id,
        time: p.updated_at || p.created_at,
        type: '处方',
        content: `${p.patient_name || '-'} ${p.diagnosis || ''}`,
        status: STATUS_LABELS[p.status] || p.status,
      }));
      return (
        <BasicTable headers={['时间', '类型', '内容', '状态']}>
          {rows.map((r) => (
            <tr key={r.id}><td>{formatDateTime(r.time)}</td><td>{r.type}</td><td>{r.content}</td><td>{r.status}</td></tr>
          ))}
        </BasicTable>
      );
    }

    if (kind === 'medicineDown') {
      return (
        <BasicTable headers={['药品', '规格', '库存', '状态', '操作']}>
          {filteredMedicines.map((m) => (
            <tr key={m.id}>
              <td><strong>{m.name}</strong></td>
              <td>{m.specification || '-'}</td>
              <td>{m.stock}</td>
              <td>{downIds.has(m.id) ? '已下架' : '在架'}</td>
              <td><button className="glass-btn glass-btn--danger glass-btn--sm" disabled={downIds.has(m.id)} onClick={() => setDownIds((prev) => new Set(prev).add(m.id))}>下架</button></td>
            </tr>
          ))}
        </BasicTable>
      );
    }

    if (kind === 'restock') {
      return (
        <BasicTable headers={['药品', '规格', '当前库存', '补药数量', '操作']}>
          {filteredMedicines.map((m) => (
            <tr key={m.id}>
              <td><strong>{m.name}</strong></td>
              <td>{m.specification || '-'}</td>
              <td>{m.stock}</td>
              <td><input className="glass-input module-basic-input" type="number" min="1" value={restockDrafts[m.id] || ''} onChange={(e) => setRestockDrafts((prev) => ({ ...prev, [m.id]: e.target.value }))} placeholder="数量" /></td>
              <td><button className="glass-btn glass-btn--primary glass-btn--sm" disabled={busyId === m.id} onClick={() => restock(m)}>确认补药</button></td>
            </tr>
          ))}
        </BasicTable>
      );
    }

    return (
      <BasicTable headers={['药品', '规格', '厂家', '单位', '库存', '库存状态']}>
        {filteredMedicines.map((m) => (
          <tr key={m.id}>
            <td><strong>{m.name}</strong></td>
            <td>{m.specification || '-'}</td>
            <td>{m.manufacturer || '-'}</td>
            <td>{m.unit}</td>
            <td>{m.stock}</td>
            <td>{Number(m.stock) <= 20 ? '低库存' : '正常'}</td>
          </tr>
        ))}
      </BasicTable>
    );
  };

  const showSearch = ['medicineSettings', 'medicineDown', 'restock', 'inventory'].includes(kind);

  return (
    <div>
      <motion.div className="page-header flex-between" initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}>
        <div className="page-title-with-icon">
          <span className="page-title-icon"><ModuleIcon name={icon} size={46} /></span>
          <div><h1>{title}</h1><p>基础功能已开放</p></div>
        </div>
        <button className="glass-btn glass-btn--outline" onClick={load}>刷新</button>
      </motion.div>

      {showSearch && (
        <div className="search-bar">
          <input className="glass-input" placeholder="搜索药品名称、厂家或规格..." value={keyword} onChange={(e) => setKeyword(e.target.value)} />
        </div>
      )}

      <motion.div className="glass-card module-basic-card" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
        {renderContent()}
      </motion.div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="module-basic-stat">
      <div className="module-basic-stat-value">{value}</div>
      <div className="module-basic-stat-label">{label}</div>
    </div>
  );
}

function BasicTable({ headers, children }: { headers: string[]; children: React.ReactNode }) {
  return (
    <table className="glass-table module-basic-table">
      <thead>
        <tr>{headers.map((h) => <th key={h}>{h}</th>)}</tr>
      </thead>
      <tbody>{children}</tbody>
    </table>
  );
}
