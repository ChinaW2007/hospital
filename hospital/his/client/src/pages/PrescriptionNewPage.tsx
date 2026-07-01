import { useState, useEffect, FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { prescriptionApi, patientApi, medicineApi } from '../services/api';
import type { Patient, Medicine, PrescriptionItemFormData } from '../types';
import Modal from '../components/Modal';
import { showToast } from '../components/Toast';

interface MedItem extends PrescriptionItemFormData {
  medicine_name?: string; specification?: string; unit?: string; price?: number;
}

const fadeUp = { initial: { opacity: 0, y: 20 }, animate: { opacity: 1, y: 0 } };

// 处方类型对应颜色
const PRESCRIPTION_COLORS: Record<string, { bg: string; border: string; label: string }> = {
  '普通': { bg: 'rgba(255,255,255,0.5)', border: 'rgba(200,200,200,0.6)', label: '普通处方' },
  '急诊': { bg: 'rgba(255,253,231,0.6)', border: 'rgba(255,213,79,0.5)', label: '急诊处方' },
  '儿科': { bg: 'rgba(232,245,233,0.6)', border: 'rgba(129,199,132,0.5)', label: '儿科处方' },
  '麻醉精一': { bg: 'rgba(255,235,238,0.6)', border: 'rgba(239,154,154,0.5)', label: '麻醉,精一处方 ' },
  '精二': { bg: 'rgba(245,245,245,0.6)', border: 'rgba(180,180,180,0.5)', label: '精二处方' },
};

export default function PrescriptionNewPage() {
  const navigate = useNavigate();

  // 处方前记
  const [prescriptionType, setPrescriptionType] = useState('普通');
  const [paymentType, setPaymentType] = useState('医保');
  const [medicalRecordNo, setMedicalRecordNo] = useState('');
  const [department, setDepartment] = useState('');
  const [bedNo, setBedNo] = useState('');

  const [patientSearch, setPatientSearch] = useState('');
  const [patients, setPatients] = useState<Patient[]>([]);
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [patientSearching, setPatientSearching] = useState(false);

  const [diagnosis, setDiagnosis] = useState('');
  const [note, setNote] = useState('');

  const [medSearch, setMedSearch] = useState('');
  const [medicines, setMedicines] = useState<Medicine[]>([]);
  const [medSearching, setMedSearching] = useState(false);
  const [items, setItems] = useState<MedItem[]>([]);

  const [medModalOpen, setMedModalOpen] = useState(false);
  const [selectedMed, setSelectedMed] = useState<Medicine | null>(null);
  const [medForm, setMedForm] = useState({ dosage: '', usage_method: '口服', frequency: '每日3次', days: 3, quantity: 1, note: '' });

  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const searchPatients = async (kw: string) => {
    if (!kw.trim()) { setPatients([]); return; }
    setPatientSearching(true);
    try { const data = await patientApi.list({ page: 1, pageSize: 10, keyword: kw }); setPatients(data.list); }
    catch (err) { console.error(err); }
    finally { setPatientSearching(false); }
  };

  const searchMedicines = async (kw: string) => {
    if (!kw.trim()) { setMedicines([]); return; }
    setMedSearching(true);
    try { const data = await medicineApi.list({ page: 1, pageSize: 10, keyword: kw }); setMedicines(data.list); }
    catch (err) { console.error(err); }
    finally { setMedSearching(false); }
  };

  useEffect(() => { const timer = setTimeout(() => searchPatients(patientSearch), 300); return () => clearTimeout(timer); }, [patientSearch]);
  useEffect(() => { const timer = setTimeout(() => searchMedicines(medSearch), 300); return () => clearTimeout(timer); }, [medSearch]);

  const selectPatient = (p: Patient) => { setSelectedPatient(p); setPatientSearch(''); setPatients([]); };

  const openMedForm = (m: Medicine) => {
    setSelectedMed(m);
    setMedForm({ dosage: '', usage_method: '口服', frequency: '每日3次', days: 3, quantity: 1, note: '' });
    setMedModalOpen(true);
  };

  const addMedItem = () => {
    if (!selectedMed || !medForm.dosage) return;
    setItems([...items, {
      medicine_id: selectedMed.id, medicine_name: selectedMed.name,
      specification: selectedMed.specification, unit: selectedMed.unit,
      drug_form: selectedMed.drug_form,
      price: selectedMed.price,
      ...medForm,
    }]);
    setMedModalOpen(false); setSelectedMed(null); setMedSearch(''); setMedicines([]);
  };

  const removeItem = (index: number) => setItems(items.filter((_, i) => i !== index));

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault(); setError('');
    if (!selectedPatient) { setError('请先选择病人'); return; }
    if (!diagnosis.trim()) { setError('请填写临床诊断'); return; }
    if (items.length === 0) { setError('请至少添加一种药品'); return; }
    if (items.length > 5) { setError('每张处方不得超过5种药品'); return; }
    setConfirmOpen(true);
  };

  const confirmSubmit = async () => {
    setConfirmOpen(false);
    setSubmitting(true);
    try {
      const res = await prescriptionApi.create({
        patient_id: selectedPatient!.id,
        prescription_type: prescriptionType, payment_type: paymentType,
        medical_record_no: medicalRecordNo, department, bed_no: bedNo,
        diagnosis: diagnosis.trim(), note: note.trim(),
        items: items.map(({ medicine_id, drug_form, dosage, usage_method, frequency, days, quantity, note }) =>
          ({ medicine_id, drug_form, dosage, usage_method, frequency, days, quantity, note })),
      });
      showToast(res.message || '处方已提交，等待药师审核', 'success');
      navigate(`/prescriptions/${res.id}`);
    } catch (err: any) { setError(err.response?.data?.error || '提交失败'); }
    finally { setSubmitting(false); }
  };

  return (
    <div>
      <motion.div className="page-header" {...fadeUp} transition={{ duration: 0.4 }}>
        <h1>✍️ 开具处方</h1>
        <p>选择病人 → 填写诊断 → 添加药品 → 提交处方</p>
      </motion.div>

      {error && <motion.div className="alert alert--error" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}>{error}</motion.div>}

      <form onSubmit={handleSubmit}>
        {/* 处方类型标签 */}
        <motion.div {...fadeUp} transition={{ delay: 0.03 }} style={{ marginBottom: 12, textAlign: 'center' }}>
          <span style={{
            display: 'inline-block', padding: '6px 20px', borderRadius: 50,
            background: PRESCRIPTION_COLORS[prescriptionType].bg,
            border: `2px solid ${PRESCRIPTION_COLORS[prescriptionType].border}`,
            fontWeight: 600, fontSize: 15, color: 'var(--text-primary)',
            backdropFilter: 'blur(10px)',
          }}>
            📋 {PRESCRIPTION_COLORS[prescriptionType].label}
          </span>
        </motion.div>

        {/* 处方前记 */}
        <motion.div className="glass-card" style={{
          padding: 20, marginBottom: 16,
          background: PRESCRIPTION_COLORS[prescriptionType].bg,
          borderColor: PRESCRIPTION_COLORS[prescriptionType].border,
        }} {...fadeUp} transition={{ delay: 0.05 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>📋 处方前记</h3>
          <div className="form-grid form-grid--3">
            <div className="form-group">
              <label>处方类型</label>
              <select className="glass-input" value={prescriptionType} onChange={(e) => setPrescriptionType(e.target.value)}>
                <option value="普通">普通处方</option>
                <option value="急诊">急诊处方</option>
                <option value="儿科">儿科处方</option>
                <option value="麻醉精一">麻、精一</option>
                <option value="精二">精二处方</option>
              </select>
            </div>
            <div className="form-group">
              <label>费别</label>
              <select className="glass-input" value={paymentType} onChange={(e) => setPaymentType(e.target.value)}>
                <option value="公费">公费医疗</option>
                <option value="医保">医疗保险</option>
                <option value="部分自费">部分自费</option>
                <option value="自费">自费</option>
              </select>
            </div>
            <div className="form-group">
              <label>病历号</label>
              <input className="glass-input" value={medicalRecordNo} onChange={(e) => setMedicalRecordNo(e.target.value)} placeholder="门诊/住院病历号" />
            </div>
            <div className="form-group">
              <label>科别</label>
              <input className="glass-input" value={department} onChange={(e) => setDepartment(e.target.value)} placeholder="如：内科、儿科" />
            </div>
            <div className="form-group">
              <label>床位号</label>
              <input className="glass-input" value={bedNo} onChange={(e) => setBedNo(e.target.value)} placeholder="如：12床" />
            </div>
          </div>
        </motion.div>

        {/* 病人选择 + 诊断 */}
        <motion.div className="glass-card" style={{
          padding: 20, marginBottom: 16,
          background: PRESCRIPTION_COLORS[prescriptionType].bg,
          borderColor: PRESCRIPTION_COLORS[prescriptionType].border,
        }} {...fadeUp} transition={{ delay: 0.08 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>① 选择病人与诊断</h3>
          {selectedPatient ? (
            <div className="flex-between" style={{ padding: '12px 16px', background: 'rgba(92,184,92,0.08)', borderRadius: 12 }}>
              <div>
                <strong>{selectedPatient.name}</strong>
                <span style={{ marginLeft: 12, color: 'var(--text-secondary)', fontSize: 14 }}>{selectedPatient.gender} · {selectedPatient.age}岁 · {selectedPatient.phone || '无手机号'}</span>
              </div>
              <button type="button" className="glass-btn glass-btn--outline glass-btn--sm" onClick={() => setSelectedPatient(null)}>更换病人</button>
            </div>
          ) : (
            <div>
              <div style={{ display: 'flex', gap: 8 }}>
                <input className="glass-input" style={{ flex: 1 }} placeholder="搜索病人姓名或手机号..." value={patientSearch} onChange={(e) => setPatientSearch(e.target.value)} />
              </div>
              {patientSearching && <div style={{ padding: 12, color: 'var(--text-muted)', fontSize: 14 }}>搜索中...</div>}
              {patients.length > 0 && (
                <div style={{ marginTop: 8, display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: 8 }}>
                  {patients.map((p) => (
                    <motion.div key={p.id} className="glass-card" style={{ padding: '14px 18px', cursor: 'pointer' }}
                      onClick={() => selectPatient(p)} whileHover={{ scale: 1.02 }}>
                      <strong style={{ fontSize: 16 }}>{p.name}</strong>
                      <span style={{ marginLeft: 12, color: 'var(--text-secondary)', fontSize: 13 }}>{p.gender} · {p.age}岁 · {p.phone || '无手机号'} · #{p.id}</span>
                    </motion.div>
                  ))}
                </div>
              )}
            </div>
          )}
          <div className="form-group mt-md">
            <label>临床诊断 *</label>
            <input className="glass-input" placeholder="请输入诊断结果，如：上呼吸道感染" value={diagnosis} onChange={(e) => setDiagnosis(e.target.value)} />
          </div>
          <div className="form-group mt-md">
            <label>备注</label>
            <textarea className="glass-input" placeholder="处方备注（可选）" rows={2} value={note} onChange={(e) => setNote(e.target.value)} />
          </div>
        </motion.div>

        {/* 处方正文 */}
        <motion.div className="glass-card" style={{
          padding: 20, marginBottom: 16,
          background: PRESCRIPTION_COLORS[prescriptionType].bg,
          borderColor: PRESCRIPTION_COLORS[prescriptionType].border,
        }} {...fadeUp} transition={{ delay: 0.15 }}>
          <div className="flex-between" style={{ marginBottom: 12 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600 }}>💊 处方正文 (Rp) — 已添加 {items.length}/5 种药品</h3>
            {items.length >= 5 && <span style={{ color: '#d9534f', fontSize: 13, fontWeight: 600 }}>⚠ 已达上限</span>}
          </div>

          {items.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <table className="glass-table">
                <thead>
                  <tr><th>药品名称</th><th>规格</th><th>用量</th><th>用法</th><th>频次</th><th>天数</th><th>数量</th><th>操作</th></tr>
                </thead>
                <tbody>
                  <AnimatePresence>
                    {items.map((item, i) => (
                      <motion.tr key={i} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }}>
                        <td><strong>{item.medicine_name}</strong></td>
                        <td style={{ fontSize: 13 }}>{item.specification}</td>
                        <td>{item.dosage}</td>
                        <td>{item.usage_method}</td>
                        <td>{item.frequency}</td>
                        <td>{item.days}天</td>
                        <td>{item.quantity}{item.unit}</td>
                        <td>
                          <button type="button" className="glass-btn glass-btn--danger glass-btn--sm" onClick={() => removeItem(i)}>删除</button>
                        </td>
                      </motion.tr>
                    ))}
                  </AnimatePresence>
                </tbody>
              </table>
            </div>
          )}

          {items.length < 5 && (
            <>
              <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                <input className="glass-input" style={{ flex: 1 }} placeholder="搜索药品名称（通用名/商品名）..." value={medSearch} onChange={(e) => setMedSearch(e.target.value)} />
              </div>
              {medSearching && <div style={{ padding: 8, color: 'var(--text-muted)', fontSize: 14 }}>搜索中...</div>}
              {medicines.length > 0 && (
                <div style={{ marginTop: 8, display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: 8 }}>
                  {medicines.map((m) => (
                    <motion.div key={m.id} className="glass-card"
                      style={{ padding: '14px 18px', cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                      onClick={() => openMedForm(m)} whileHover={{ scale: 1.02 }}>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <strong style={{ fontSize: 16 }}>{m.name}</strong>
                        {m.generic_name && <span style={{ marginLeft: 6, color: 'var(--blue)', fontSize: 12 }}>({m.generic_name})</span>}
                        <span style={{ marginLeft: 8, color: 'var(--text-muted)', fontSize: 13 }}>{m.specification} · {m.drug_form}</span>
                      </div>
                      <div style={{ fontSize: 14, color: 'var(--text-secondary)', whiteSpace: 'nowrap', marginLeft: 12 }}>
                        ¥{Number(m.price).toFixed(2)} · {m.stock}{m.unit}
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}
            </>
          )}
        </motion.div>

        <motion.div style={{ display: 'flex', gap: 12 }} {...fadeUp} transition={{ delay: 0.2 }}>
          <motion.button className="glass-btn glass-btn--primary glass-btn--lg" type="submit" disabled={submitting} whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
            {submitting ? '提交中...' : '📤 提交处方'}
          </motion.button>
          <button className="glass-btn glass-btn--outline" type="button" onClick={() => navigate(-1)}>返回</button>
        </motion.div>
      </form>

      {/* 提交确认对话框 */}
      <AnimatePresence>
        {confirmOpen && (
          <motion.div className="confirm-overlay" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <motion.div className="confirm-dialog glass-card" initial={{ scale: 0.9, y: 20 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.9, y: 20 }}>
              <h3>📋 确认开具处方</h3>
              <div style={{ textAlign: 'left', margin: '16px 0', fontSize: 14, lineHeight: 2 }}>
                <div><strong>处方类型：</strong>{PRESCRIPTION_COLORS[prescriptionType].label}</div>
                <div><strong>病人：</strong>{selectedPatient?.name} ({selectedPatient?.gender} · {selectedPatient?.age}岁)</div>
                <div><strong>诊断：</strong><span style={{ color: 'var(--blue)' }}>{diagnosis}</span></div>
                <div><strong>药品数量：</strong>{items.length} 种</div>
                <div style={{ marginTop: 8, padding: '8px 12px', background: 'rgba(0,0,0,0.03)', borderRadius: 8 }}>
                  {items.map((item, i) => (
                    <div key={i}>💊 {item.medicine_name} — {item.dosage} · {item.usage_method} · {item.frequency} × {item.days}天 × {item.quantity}{item.unit}</div>
                  ))}
                </div>
              </div>
              <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 20 }}>请仔细核对处方信息，提交后将进入药师审核流程。</p>
              <div className="confirm-actions">
                <motion.button className="glass-btn glass-btn--primary" onClick={confirmSubmit} whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>✅ 确认提交</motion.button>
                <button className="glass-btn glass-btn--outline" onClick={() => setConfirmOpen(false)}>取消</button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Medicine dosage modal */}
      <Modal isOpen={medModalOpen} onClose={() => { setMedModalOpen(false); setSelectedMed(null); }} title={selectedMed ? `添加药品: ${selectedMed.name}` : '添加药品'}>
        <div style={{ marginBottom: 12, fontSize: 14, color: 'var(--text-secondary)' }}>
          {selectedMed?.specification} · ¥{selectedMed ? Number(selectedMed.price).toFixed(2) : '0.00'}
        </div>
        <div className="form-grid form-grid--3">
          <div className="form-group">
            <label>用量 *</label>
            <input className="glass-input" placeholder="如 1片、10ml" value={medForm.dosage} onChange={(e) => setMedForm({ ...medForm, dosage: e.target.value })} autoFocus />
          </div>
          <div className="form-group">
            <label>用法</label>
            <select className="glass-input" value={medForm.usage_method} onChange={(e) => setMedForm({ ...medForm, usage_method: e.target.value })}>
              <option value="口服">口服</option><option value="外用">外用</option><option value="注射">注射</option><option value="含服">含服</option><option value="吸入">吸入</option>
            </select>
          </div>
          <div className="form-group">
            <label>频次</label>
            <select className="glass-input" value={medForm.frequency} onChange={(e) => setMedForm({ ...medForm, frequency: e.target.value })}>
              <option value="每日1次">每日1次</option><option value="每日2次">每日2次</option><option value="每日3次">每日3次</option><option value="每日4次">每日4次</option><option value="睡前1次">睡前1次</option><option value="必要时">必要时</option>
            </select>
          </div>
          <div className="form-group"><label>天数</label><input className="glass-input" type="number" value={medForm.days} onChange={(e) => setMedForm({ ...medForm, days: parseInt(e.target.value) || 1 })} /></div>
          <div className="form-group"><label>数量</label><input className="glass-input" type="number" value={medForm.quantity} onChange={(e) => setMedForm({ ...medForm, quantity: parseInt(e.target.value) || 1 })} /></div>
          <div className="form-group"><label>备注</label><input className="glass-input" placeholder="如饭后服用" value={medForm.note} onChange={(e) => setMedForm({ ...medForm, note: e.target.value })} /></div>
        </div>
        <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
          <motion.button className="glass-btn glass-btn--success" type="button" onClick={addMedItem} whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>✓ 确认添加</motion.button>
          <button className="glass-btn glass-btn--outline" type="button" onClick={() => { setMedModalOpen(false); setSelectedMed(null); }}>取消</button>
        </div>
      </Modal>
    </div>
  );
}
