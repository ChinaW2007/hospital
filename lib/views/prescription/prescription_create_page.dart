import 'package:flutter/material.dart';
import 'package:dio/dio.dart';
import 'package:his_mobile/core/network/api_client.dart';
import 'package:his_mobile/data/models/patient_model.dart';
import 'package:his_mobile/data/models/medicine_model.dart';
import 'package:his_mobile/core/theme/glass_card.dart';
import 'package:his_mobile/core/widgets/animated_scale_button.dart';


class PrescriptionCreatePage extends StatefulWidget {
  const PrescriptionCreatePage({super.key});

  @override
  State<PrescriptionCreatePage> createState() => _PrescriptionCreatePageState();
}

class _PrescriptionCreatePageState extends State<PrescriptionCreatePage> {
  final _formKey = GlobalKey<FormState>();

  // 处方头信息
  String _prescriptionType = '普通';
  String _paymentType = '医保';
  final _departmentController = TextEditingController();
  final _bedNoController = TextEditingController();
  final _diagnosisController = TextEditingController();
  final _noteController = TextEditingController();

  PatientModel? _selectedPatient;
  final List<Map<String, dynamic>> _selectedItems = []; // 包含 medicine, dosage, usage, frequency, days, quantity, trace_code, note
  bool _isLoading = false;

  final List<String> _prescriptionTypes = ['普通', '急诊', '儿科', '麻醉精一', '精二'];
  final List<String> _paymentTypes = ['自费', '医保', '公费', '部分自费'];
  final List<String> _usageMethods = ['口服', '外用', '注射', '含服', '吸入'];
  final List<String> _frequencies = ['每日1次', '每日2次', '每日3次', '每日4次', '睡前1次', '必要时'];

  @override
  void dispose() {
    _departmentController.dispose();
    _bedNoController.dispose();
    _diagnosisController.dispose();
    _noteController.dispose();
    super.dispose();
  }

  // 弹出选择患者底部抽屉
  void _showPatientSelector() async {
    final List<PatientModel> patientList = [];
    bool listLoading = false;
    String searchKeyword = '';
    
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setSheetState) {
            
            Future<void> fetchPatients() async {
              setSheetState(() => listLoading = true);
              try {
                final res = await ApiClient().dio.get('/api/patients', queryParameters: {'keyword': searchKeyword, 'pageSize': 20});
                final list = res.data['list'] as List? ?? [];
                setSheetState(() {
                  patientList.clear();
                  patientList.addAll(list.map((p) => PatientModel.fromJson(p as Map<String, dynamic>)));
                });
              } catch (_) {}
              setSheetState(() => listLoading = false);
            }

            return Container(
              height: MediaQuery.of(context).size.height * 0.75,
              padding: const EdgeInsets.all(20.0),
              child: Column(
                children: [
                  const Text('选择就诊患者', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 12),
                  // 搜索栏
                  TextField(
                    decoration: const InputDecoration(
                      labelText: '搜索患者姓名/手机号',
                      prefixIcon: Icon(Icons.search),
                    ),
                    onSubmitted: (val) {
                      searchKeyword = val.trim();
                      fetchPatients();
                    },
                  ),
                  const SizedBox(height: 16),
                  Expanded(
                    child: listLoading
                        ? const Center(child: CircularProgressIndicator())
                        : patientList.isEmpty
                            ? const Center(child: Text('输入关键字并按回车搜索患者', style: TextStyle(color: Colors.grey)))
                            : ListView.builder(
                                itemCount: patientList.length,
                                itemBuilder: (context, index) {
                                  final p = patientList[index];
                                  return ListTile(
                                    title: Text(p.name, style: const TextStyle(fontWeight: FontWeight.bold)),
                                    subtitle: Text('病历号: ${p.medicalRecordNo} | 年龄: ${p.age}'),
                                    trailing: const Icon(Icons.chevron_right),
                                    onTap: () {
                                      setState(() {
                                        _selectedPatient = p;
                                      });
                                      Navigator.pop(context);
                                    },
                                  );
                                },
                              ),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }



  void _showErrorSnackbar(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg), backgroundColor: Colors.redAccent));
  }

  // 弹出选择药品与配置单项信息对话框
  void _showMedicineSelector() {
    final List<MedicineModel> medList = [];
    bool listLoading = false;
    String searchKeyword = '';

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setSheetState) {
            
            Future<void> fetchMedicines() async {
              setSheetState(() => listLoading = true);
              try {
                final res = await ApiClient().dio.get('/api/medicines', queryParameters: {'keyword': searchKeyword, 'pageSize': 20});
                final list = res.data['list'] as List? ?? [];
                setSheetState(() {
                  medList.clear();
                  medList.addAll(list.map((m) => MedicineModel.fromJson(m as Map<String, dynamic>)));
                });
              } catch (_) {}
              setSheetState(() => listLoading = false);
            }

            return Container(
              height: MediaQuery.of(context).size.height * 0.75,
              padding: const EdgeInsets.all(20.0),
              child: Column(
                children: [
                  const Text('选择处方药品', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 12),
                  TextField(
                    decoration: const InputDecoration(
                      labelText: '搜索药品名/生产厂家',
                      prefixIcon: Icon(Icons.search),
                    ),
                    onSubmitted: (val) {
                      searchKeyword = val.trim();
                      fetchMedicines();
                    },
                  ),
                  const SizedBox(height: 16),
                  Expanded(
                    child: listLoading
                        ? const Center(child: CircularProgressIndicator())
                        : medList.isEmpty
                            ? const Center(child: Text('输入关键字并搜索药品', style: TextStyle(color: Colors.grey)))
                            : ListView.builder(
                                itemCount: medList.length,
                                itemBuilder: (context, index) {
                                  final m = medList[index];
                                  return ListTile(
                                    title: Text(m.name, style: const TextStyle(fontWeight: FontWeight.bold)),
                                    subtitle: Text('规格: ${m.specification ?? "无"} | 厂商: ${m.manufacturer ?? "未知"} | 库存: ${m.stock}'),
                                    trailing: Text('¥${m.price.toStringAsFixed(2)}/${m.unit}'),
                                    onTap: () {
                                      Navigator.pop(context);
                                      if (_selectedItems.any((item) => item['medicine'].id == m.id)) {
                                        _showErrorSnackbar('处方中已包含此药品');
                                        return;
                                      }
                                      _showMedicineFormDialog(m);
                                    },
                                  );
                                },
                              ),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  // 配置单个药品的具体用量、追溯码等
  void _showMedicineFormDialog(MedicineModel medicine, {String traceCode = ''}) {
    final formKey = GlobalKey<FormState>();
    final dosageController = TextEditingController(text: '1片/次');
    final daysController = TextEditingController(text: '3');
    final quantityController = TextEditingController(text: '1');
    final traceController = TextEditingController(text: traceCode);
    final noteController = TextEditingController();

    String usageMethod = '口服';
    String frequency = '每日3次';

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            


            return AlertDialog(
              title: Text('配置 [${medicine.name}] 用量'),
              content: SingleChildScrollView(
                child: Form(
                  key: formKey,
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      // 用量
                      TextFormField(
                        controller: dosageController,
                        decoration: const InputDecoration(labelText: '单次剂量 (如: 1片/次)'),
                        validator: (v) => v!.isEmpty ? '必填' : null,
                      ),
                      const SizedBox(height: 12),
                      
                      // 用法 & 频次 同行
                      Row(
                        children: [
                          Expanded(
                            child: DropdownButtonFormField<String>(
                              value: usageMethod,
                              decoration: const InputDecoration(labelText: '用法'),
                              items: _usageMethods.map((u) => DropdownMenuItem(value: u, child: Text(u))).toList(),
                              onChanged: (v) => setDialogState(() => usageMethod = v!),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: DropdownButtonFormField<String>(
                              value: frequency,
                              decoration: const InputDecoration(labelText: '频次'),
                              items: _frequencies.map((f) => DropdownMenuItem(value: f, child: Text(f))).toList(),
                              onChanged: (v) => setDialogState(() => frequency = v!),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      
                      // 天数 & 数量
                      Row(
                        children: [
                          Expanded(
                            child: TextFormField(
                              controller: daysController,
                              keyboardType: TextInputType.number,
                              decoration: const InputDecoration(labelText: '天数 (如: 3)'),
                              validator: (v) => int.tryParse(v ?? '') == null ? '整数' : null,
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: TextFormField(
                              controller: quantityController,
                              keyboardType: TextInputType.number,
                              decoration: const InputDecoration(labelText: '总开药数量 (件)'),
                              validator: (v) => int.tryParse(v ?? '') == null ? '整数' : null,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      
                      TextFormField(
                        controller: traceController,
                        decoration: const InputDecoration(
                          labelText: '20位追溯码',
                          hintText: '请输入该药品20位追溯码',
                        ),
                        validator: (v) => v!.trim().isEmpty ? '追溯码必填' : null,
                      ),
                      const SizedBox(height: 12),
                      
                      // 备注
                      TextFormField(
                        controller: noteController,
                        decoration: const InputDecoration(labelText: '备注说明 (选填)'),
                      ),
                    ],
                  ),
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(context),
                  child: const Text('取消'),
                ),
                ElevatedButton(
                  onPressed: () {
                    if (!formKey.currentState!.validate()) return;
                    
                    setState(() {
                      _selectedItems.add({
                        'medicine': medicine,
                        'dosage': dosageController.text.trim(),
                        'usage_method': usageMethod,
                        'frequency': frequency,
                        'days': int.parse(daysController.text),
                        'quantity': int.parse(quantityController.text),
                        'trace_code': traceController.text.trim(),
                        'note': noteController.text.trim(),
                      });
                    });
                    
                    Navigator.pop(context);
                  },
                  child: const Text('添加'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  // 计算处方总价
  double _calculateTotalAmount() {
    double total = 0;
    for (var item in _selectedItems) {
      final med = item['medicine'] as MedicineModel;
      final qty = item['quantity'] as int;
      total += med.price * qty;
    }
    return total;
  }

  // 提交处方到 HIS 后端
  Future<void> _submitPrescription() async {
    if (_selectedPatient == null) {
      _showErrorSnackbar('请先选择就诊患者');
      return;
    }
    if (_diagnosisController.text.trim().isEmpty) {
      _showErrorSnackbar('请输入临床诊断');
      return;
    }
    if (_selectedItems.isEmpty) {
      _showErrorSnackbar('请至少选择一种药品明细');
      return;
    }

    setState(() {
      _isLoading = true;
    });

    final payload = {
      'patient_id': _selectedPatient!.id,
      'prescription_type': _prescriptionType,
      'payment_type': _paymentType,
      'medical_record_no': _selectedPatient!.medicalRecordNo,
      'department': _departmentController.text.trim(),
      'bed_no': _bedNoController.text.trim(),
      'diagnosis': _diagnosisController.text.trim(),
      'note': _noteController.text.trim(),
      'items': _selectedItems.map((item) {
        final med = item['medicine'] as MedicineModel;
        return {
          'medicine_id': med.id,
          'dosage': item['dosage'],
          'usage_method': item['usage_method'],
          'frequency': item['frequency'],
          'days': item['days'],
          'quantity': item['quantity'],
          'trace_code': item['trace_code'],
          'note': item['note'],
        };
      }).toList(),
    };

    try {
      final response = await ApiClient().dio.post('/api/prescriptions', data: payload);
      if (response.statusCode == 201) {
        final code = response.data['prescription_code'];
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('处方已提交成功！编号: $code'), backgroundColor: Colors.green),
        );
        Navigator.pop(context, true); // 成功返回
      }
    } on DioException catch (e) {
      final err = e.response?.data?['error']?.toString() ?? '处方提交失败';
      _showErrorSnackbar(err);
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        title: const Text('开具处方'),
        backgroundColor: Colors.transparent,
        elevation: 0,
      ),
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: isDark
                ? [const Color(0xFF090C15), const Color(0xFF0B1B2A), const Color(0xFF141221)]
                : [const Color(0xFFEAF6FF), const Color(0xFFEDFDF8), const Color(0xFFFFF2F7)],
          ),
        ),
        child: _isLoading
            ? const Center(child: CircularProgressIndicator(color: Color(0xFF00796B)))
            : SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(20.0, 16.0, 20.0, 120.0), // 留够底部空间防止导航栏遮挡
                child: Form(
                  key: _formKey,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      // 板块一：患者与费别
                      GlassCard(
                        margin: const EdgeInsets.only(bottom: 16),
                        padding: const EdgeInsets.all(20.0),
                        borderRadius: 24,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('患者就诊档案', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w800, color: Colors.grey)),
                            const SizedBox(height: 16),
                            _selectedPatient == null
                                ? Center(
                                    child: AnimatedScaleButton(
                                      onTap: _showPatientSelector,
                                      child: Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                                        decoration: BoxDecoration(
                                          color: const Color(0xFF00796B).withValues(alpha: 0.1),
                                          borderRadius: BorderRadius.circular(16),
                                          border: Border.all(color: const Color(0xFF00796B), width: 1.5),
                                        ),
                                        child: const Row(
                                          mainAxisSize: MainAxisSize.min,
                                          children: [
                                            Icon(Icons.person_add_rounded, color: Color(0xFF00796B), size: 18),
                                            SizedBox(width: 8),
                                            Text('选择就诊患者', style: TextStyle(color: Color(0xFF00796B), fontWeight: FontWeight.w800)),
                                          ],
                                        ),
                                      ),
                                    ),
                                  )
                                : Row(
                                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                    children: [
                                      Expanded(
                                        child: Column(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            Text(
                                              '${_selectedPatient!.name} (${_selectedPatient!.gender} · ${_selectedPatient!.age}岁)',
                                              style: TextStyle(
                                                fontWeight: FontWeight.w900, 
                                                fontSize: 17,
                                                color: isDark ? Colors.white : const Color(0xFF1E293B),
                                              ),
                                            ),
                                            const SizedBox(height: 4),
                                            Text(
                                              '病历号: ${_selectedPatient!.medicalRecordNo}', 
                                              style: const TextStyle(fontSize: 13, color: Colors.grey),
                                            ),
                                          ],
                                        ),
                                      ),
                                      AnimatedScaleButton(
                                        onTap: _showPatientSelector,
                                        child: Container(
                                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                                          decoration: BoxDecoration(
                                            color: const Color(0xFF00796B).withValues(alpha: 0.08),
                                            borderRadius: BorderRadius.circular(12),
                                          ),
                                          child: const Text('更换患者', style: TextStyle(color: Color(0xFF00796B), fontWeight: FontWeight.bold, fontSize: 13)),
                                        ),
                                      )
                                    ],
                                  ),
                          ],
                        ),
                      ),

                      // 板块二：处方前记属性
                      GlassCard(
                        margin: const EdgeInsets.only(bottom: 16),
                        padding: const EdgeInsets.all(20.0),
                        borderRadius: 24,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('处方属性', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w800, color: Colors.grey)),
                            const SizedBox(height: 16),
                            Row(
                              children: [
                                Expanded(
                                  child: DropdownButtonFormField<String>(
                                    value: _prescriptionType,
                                    decoration: const InputDecoration(labelText: '处方类型'),
                                    items: _prescriptionTypes.map((t) => DropdownMenuItem(value: t, child: Text(t))).toList(),
                                    onChanged: (v) => setState(() => _prescriptionType = v!),
                                  ),
                                ),
                                const SizedBox(width: 14),
                                Expanded(
                                  child: DropdownButtonFormField<String>(
                                    value: _paymentType,
                                    decoration: const InputDecoration(labelText: '支付费别'),
                                    items: _paymentTypes.map((t) => DropdownMenuItem(value: t, child: Text(t))).toList(),
                                    onChanged: (v) => setState(() => _paymentType = v!),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 16),
                            Row(
                              children: [
                                Expanded(
                                  child: TextFormField(
                                    controller: _departmentController,
                                    decoration: const InputDecoration(labelText: '就诊科别 (如: 内科)', prefixIcon: Icon(Icons.home_work_outlined)),
                                  ),
                                ),
                                const SizedBox(width: 14),
                                Expanded(
                                  child: TextFormField(
                                    controller: _bedNoController,
                                    decoration: const InputDecoration(labelText: '床位号 (选填)', prefixIcon: Icon(Icons.bed_outlined)),
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),

                      // 板块三：临床诊断
                      GlassCard(
                        margin: const EdgeInsets.only(bottom: 16),
                        padding: const EdgeInsets.all(20.0),
                        borderRadius: 24,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('临床诊断', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w800, color: Colors.grey)),
                            const SizedBox(height: 12),
                            TextFormField(
                              controller: _diagnosisController,
                              maxLines: 2,
                              decoration: const InputDecoration(
                                hintText: '请输入本次就诊的临床诊断结论...',
                              ),
                            ),
                          ],
                        ),
                      ),

                      // 板块四：处方药品明细
                      GlassCard(
                        margin: const EdgeInsets.only(bottom: 16),
                        padding: const EdgeInsets.all(20.0),
                        borderRadius: 24,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                const Text('药品明细 (最多5种)', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w800, color: Colors.grey)),
                                AnimatedScaleButton(
                                  onTap: _showMedicineSelector,
                                  child: Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                                    decoration: BoxDecoration(
                                      color: const Color(0xFF00796B).withValues(alpha: 0.08),
                                      borderRadius: BorderRadius.circular(12),
                                    ),
                                    child: const Row(
                                      children: [
                                        Icon(Icons.add_rounded, color: Color(0xFF00796B), size: 16),
                                        SizedBox(width: 4),
                                        Text('添加药品', style: TextStyle(color: Color(0xFF00796B), fontWeight: FontWeight.bold, fontSize: 13)),
                                      ],
                                    ),
                                  ),
                                ),
                              ],
                            ),
                            const Divider(height: 24, color: Colors.black12),
                            _selectedItems.isEmpty
                                ? const Center(
                                    child: Padding(
                                      padding: EdgeInsets.symmetric(vertical: 32.0),
                                      child: Text('请添加处方药品明细', style: TextStyle(color: Colors.grey, fontSize: 13)),
                                    ),
                                  )
                                : ListView.builder(
                                    shrinkWrap: true,
                                    physics: const NeverScrollableScrollPhysics(),
                                    itemCount: _selectedItems.length,
                                    itemBuilder: (context, index) {
                                      final item = _selectedItems[index];
                                      final med = item['medicine'] as MedicineModel;
                                      
                                      return Container(
                                        margin: const EdgeInsets.only(bottom: 12),
                                        padding: const EdgeInsets.all(12),
                                        decoration: BoxDecoration(
                                          color: isDark ? Colors.white.withValues(alpha: 0.04) : Colors.white.withValues(alpha: 0.4),
                                          borderRadius: BorderRadius.circular(16),
                                          border: Border.all(color: isDark ? Colors.white10 : Colors.black12),
                                        ),
                                        child: Row(
                                          children: [
                                            Expanded(
                                              child: Column(
                                                crossAxisAlignment: CrossAxisAlignment.start,
                                                children: [
                                                  Text(
                                                    med.name,
                                                    style: TextStyle(
                                                      fontWeight: FontWeight.bold, 
                                                      fontSize: 15,
                                                      color: isDark ? Colors.white : const Color(0xFF1E293B),
                                                    ),
                                                  ),
                                                  const SizedBox(height: 6),
                                                  Text(
                                                    '${item['dosage']} | ${item['usage_method']} | ${item['frequency']} | ${item['days']}天 | 数量:${item['quantity']}\n追溯码: ${item['trace_code']}',
                                                    style: const TextStyle(fontSize: 12, color: Colors.grey, height: 1.4),
                                                  ),
                                                ],
                                              ),
                                            ),
                                            const SizedBox(width: 8),
                                            AnimatedScaleButton(
                                              onTap: () {
                                                setState(() {
                                                  _selectedItems.removeAt(index);
                                                });
                                              },
                                              child: Container(
                                                padding: const EdgeInsets.all(8),
                                                decoration: BoxDecoration(
                                                  color: Colors.red.withValues(alpha: 0.1),
                                                  shape: BoxShape.circle,
                                                ),
                                                child: const Icon(Icons.remove_circle_outline_rounded, color: Colors.red, size: 20),
                                              ),
                                            ),
                                          ],
                                        ),
                                      );
                                    },
                                  ),
                          ],
                        ),
                      ),

                      // 备注
                      GlassCard(
                        margin: const EdgeInsets.only(bottom: 24),
                        padding: const EdgeInsets.all(20.0),
                        borderRadius: 24,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('处方备注', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w800, color: Colors.grey)),
                            const SizedBox(height: 12),
                            TextField(
                              controller: _noteController,
                              decoration: const InputDecoration(
                                labelText: '处方备注 (选填)', 
                                hintText: '给药师的留言或要求...',
                              ),
                            ),
                          ],
                        ),
                      ),

                      // 统计与提交
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            '处方金额: ¥${_calculateTotalAmount().toStringAsFixed(2)}',
                            style: TextStyle(
                              fontSize: 18, 
                              fontWeight: FontWeight.w900, 
                              color: isDark ? const Color(0xFF4DB6AC) : const Color(0xFF00796B),
                            ),
                          ),
                          AnimatedScaleButton(
                            onTap: _submitPrescription,
                            child: Container(
                              padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 14),
                              decoration: BoxDecoration(
                                color: const Color(0xFF00796B),
                                borderRadius: BorderRadius.circular(16),
                                boxShadow: [
                                  BoxShadow(
                                    color: const Color(0xFF00796B).withValues(alpha: 0.2),
                                    blurRadius: 8,
                                    offset: const Offset(0, 4),
                                  )
                                ],
                              ),
                              child: const Text(
                                '提交处方',
                                style: TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 15),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
      ),
    );
  }
}
