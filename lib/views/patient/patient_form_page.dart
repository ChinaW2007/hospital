import 'package:flutter/material.dart';
import 'dart:math';
import 'package:dio/dio.dart';
import 'package:his_mobile/core/network/api_client.dart';
import 'package:his_mobile/data/models/patient_model.dart';

class PatientFormPage extends StatefulWidget {
  final PatientModel? patient; // 如果有值则为“编辑”，无值则为“新增”

  const PatientFormPage({super.key, this.patient});

  @override
  State<PatientFormPage> createState() => _PatientFormPageState();
}

class _PatientFormPageState extends State<PatientFormPage> {
  final _formKey = GlobalKey<FormState>();
  
  final _nameController = TextEditingController();
  final _ageController = TextEditingController();
  final _medRecordController = TextEditingController();
  final _phoneController = TextEditingController();
  
  String _gender = '男'; // 默认男
  bool _isLoading = false;

  bool get isEdit => widget.patient != null;

  @override
  void initState() {
    super.initState();
    if (isEdit) {
      final p = widget.patient!;
      _nameController.text = p.name;
      _ageController.text = p.age.toString();
      _medRecordController.text = p.medicalRecordNo;
      _phoneController.text = p.phone ?? '';
      _gender = p.gender;
    } else {
      _generateMedicalRecordNo(); // 自动生成一个病历号，极大提升医生录入体验
    }
  }

  @override
  void dispose() {
    _nameController.dispose();
    _ageController.dispose();
    _medRecordController.dispose();
    _phoneController.dispose();
    super.dispose();
  }

  // 自动生成病历号（格式：HZ + 年月日时分秒 + 3位随机数）
  void _generateMedicalRecordNo() {
    final now = DateTime.now();
    final random = Random().nextInt(900) + 100; // 100-999
    final dateStr = '${now.year}${now.month.toString().padLeft(2, '0')}${now.day.toString().padLeft(2, '0')}';
    _medRecordController.text = 'HZ$dateStr$random';
  }

  Future<void> _submitForm() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _isLoading = true;
    });

    final payload = {
      'name': _nameController.text.trim(),
      'age': int.parse(_ageController.text),
      'gender': _gender,
      'medical_record_no': _medRecordController.text.trim(),
      'id_card': _medRecordController.text.trim(),
      'phone': _phoneController.text.trim(),
    };

    try {
      Response response;
      if (isEdit) {
        response = await ApiClient().dio.put(
          '/api/patients/${widget.patient!.id}',
          data: payload,
        );
      } else {
        response = await ApiClient().dio.post(
          '/api/patients',
          data: payload,
        );
      }

      if ((response.statusCode == 200 || response.statusCode == 201) && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(isEdit ? '患者信息已更新' : '成功录入新患者')),
        );
        Navigator.pop(context, true); // 返回并通知刷新
      }
    } on DioException catch (e) {
      String errStr = '操作失败';
      if (e.response != null && e.response!.data != null) {
        errStr = e.response!.data['error']?.toString() ?? errStr;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(errStr)),
      );
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
        title: Text(isEdit ? '编辑患者信息' : '录入新患者'),
      ),
      body: Container(
        height: double.infinity,
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
            ? const Center(child: CircularProgressIndicator())
            : SingleChildScrollView(
                padding: const EdgeInsets.all(20.0),
                child: Form(
                  key: _formKey,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      // 姓名
                      TextFormField(
                        controller: _nameController,
                        decoration: const InputDecoration(
                          labelText: '患者姓名',
                          prefixIcon: Icon(Icons.person_outline),
                        ),
                        validator: (value) {
                          if (value == null || value.trim().isEmpty) {
                            return '请输入患者姓名';
                          }
                          return null;
                        },
                      ),
                      const SizedBox(height: 16),

                      // 年龄与性别同行
                      Row(
                        children: [
                          Expanded(
                            child: TextFormField(
                              controller: _ageController,
                              keyboardType: TextInputType.number,
                              decoration: const InputDecoration(
                                labelText: '年龄',
                                prefixIcon: Icon(Icons.cake_outlined),
                              ),
                              validator: (value) {
                                if (value == null || value.isEmpty) {
                                  return '请输入年龄';
                                }
                                final age = int.tryParse(value);
                                if (age == null || age <= 0 || age > 130) {
                                  return '输入有效年龄';
                                }
                                return null;
                              },
                            ),
                          ),
                          const SizedBox(width: 16),
                          Expanded(
                            child: Container(
                              padding: const EdgeInsets.symmetric(horizontal: 12),
                              decoration: BoxDecoration(
                                color: isDark ? const Color(0xFF1E293B) : const Color(0xFFF1F5F9),
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: DropdownButtonHideUnderline(
                                child: DropdownButtonFormField<String>(
                                  value: _gender,
                                  decoration: const InputDecoration(
                                    labelText: '性别',
                                    filled: false,
                                    contentPadding: EdgeInsets.zero,
                                  ),
                                  items: const [
                                    DropdownMenuItem(value: '男', child: Text('男')),
                                    DropdownMenuItem(value: '女', child: Text('女')),
                                  ],
                                  onChanged: (value) {
                                    if (value != null) {
                                      setState(() {
                                        _gender = value;
                                      });
                                    }
                                  },
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),

                      // 病历号
                      Row(
                        children: [
                          Expanded(
                            child: TextFormField(
                              controller: _medRecordController,
                              decoration: const InputDecoration(
                                labelText: '病历号',
                                prefixIcon: Icon(Icons.badge_outlined),
                              ),
                              enabled: !isEdit, // 编辑时病历号通常不可修改
                              validator: (value) {
                                if (value == null || value.trim().isEmpty) {
                                  return '请输入或生成病历号';
                                }
                                return null;
                              },
                            ),
                          ),
                          if (!isEdit) ...[
                            const SizedBox(width: 8),
                            IconButton(
                              icon: const Icon(Icons.cached, color: Colors.blue),
                              onPressed: _generateMedicalRecordNo,
                              tooltip: '重新生成',
                            )
                          ],
                        ],
                      ),
                      const SizedBox(height: 16),

                      // 手机号
                      TextFormField(
                        controller: _phoneController,
                        keyboardType: TextInputType.phone,
                        decoration: const InputDecoration(
                          labelText: '手机号码 (选填)',
                          prefixIcon: Icon(Icons.phone_outlined),
                        ),
                        validator: (value) {
                          if (value != null && value.isNotEmpty) {
                            if (!RegExp(r'^1[3-9]\d{9}$').hasMatch(value)) {
                              return '请输入正确的手机号码格式';
                            }
                          }
                          return null;
                        },
                      ),
                      const SizedBox(height: 36),

                      // 提交按钮
                      ElevatedButton(
                        onPressed: _submitForm,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF00796B),
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(vertical: 16),
                        ),
                        child: Text(isEdit ? '保存修改' : '确认录入'),
                      ),
                    ],
                  ),
                ),
              ),
      ),
    );
  }
}
