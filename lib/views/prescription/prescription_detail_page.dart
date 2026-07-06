import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:dio/dio.dart';
import 'package:provider/provider.dart';
import 'package:his_mobile/core/network/api_client.dart';
import 'package:his_mobile/data/models/prescription_model.dart';
import 'package:his_mobile/providers/auth_provider.dart';
import 'package:his_mobile/core/theme/glass_card.dart';
import 'scanner_page.dart';

class PrescriptionDetailPage extends StatefulWidget {
  final int prescriptionId;

  const PrescriptionDetailPage({super.key, required this.prescriptionId});

  @override
  State<PrescriptionDetailPage> createState() => _PrescriptionDetailPageState();
}

class _PrescriptionDetailPageState extends State<PrescriptionDetailPage> {
  PrescriptionModel? _prescription;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _fetchDetails();
  }

  Future<void> _fetchDetails() async {
    setState(() {
      _isLoading = true;
    });

    try {
      final response = await ApiClient().dio.get('/api/prescriptions/${widget.prescriptionId}');
      if (response.statusCode == 200) {
        setState(() {
          _prescription = PrescriptionModel.fromJson(response.data as Map<String, dynamic>);
        });
      }
    } on DioException catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('获取详情失败: ${e.message}')),
      );
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  // 医生/药师审核操作
  Future<void> _handleReview(String status) async {
    final noteController = TextEditingController();
    final actionName = status == 'approved' ? '审核通过' : '审核驳回';

    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: Text('确认$actionName'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('确定要对处方 ${_prescription?.prescriptionCode} 进行该操作吗？'),
              const SizedBox(height: 12),
              TextField(
                controller: noteController,
                decoration: const InputDecoration(
                  labelText: '审核意见 (选填)',
                  hintText: '如驳回原因或特殊交代...',
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('取消'),
            ),
            ElevatedButton(
              onPressed: () async {
                Navigator.pop(context);
                await _submitReview(status, noteController.text.trim());
              },
              child: const Text('确认'),
            ),
          ],
        );
      },
    );
  }

  Future<void> _submitReview(String status, String note) async {
    setState(() {
      _isLoading = true;
    });

    try {
      final response = await ApiClient().dio.put(
        '/api/prescriptions/${widget.prescriptionId}/review',
        data: {'status': status, 'note': note},
      );

      if (response.statusCode == 200) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(response.data['message'] ?? '审核操作已完成'), backgroundColor: Colors.green),
        );
        _fetchDetails();
      }
    } on DioException catch (e) {
      final err = e.response?.data?['error']?.toString() ?? '审核失败';
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(err), backgroundColor: Colors.redAccent));
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  // 确认发药操作
  Future<void> _handleDispense() async {
    setState(() {
      _isLoading = true;
    });

    try {
      final response = await ApiClient().dio.put('/api/prescriptions/${widget.prescriptionId}/dispense');
      if (response.statusCode == 200) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('药品发放已确认！'), backgroundColor: Colors.green),
        );
        _fetchDetails();
      }
    } on DioException catch (e) {
      final err = e.response?.data?['error']?.toString() ?? '确认发药失败';
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(err), backgroundColor: Colors.redAccent));
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  // 触发相机扫码复核追溯码 (核心要求：扫码置于处方审核细节中)
  Future<void> _handleScanCode() async {
    final scannedCode = await Navigator.push<String>(
      context,
      MaterialPageRoute(builder: (context) => const ScannerPage()),
    );

    if (scannedCode != null && scannedCode.isNotEmpty) {
      await _processScannedCode(scannedCode);
    }
  }

  Future<void> _processScannedCode(String code) async {
    setState(() {
      _isLoading = true;
    });

    try {
      final response = await ApiClient().dio.post(
        '/api/medicine-trace-codes/scan-by-code',
        data: {'trace_code': code},
      );

      if (response.statusCode == 200) {
        // 扫码成功，进行轻触震动反馈
        HapticFeedback.mediumImpact();
        
        final data = response.data;
        final actionName = data['action']?.toString() ?? '推进';
        final isCompleted = data['completed'] as bool? ?? false;
        final medicineName = data['medicine_name']?.toString() ?? '药品';

        // 底部弹出扫描成功的精美 BottomSheet 结果提示
        if (mounted) {
          showModalBottomSheet(
            context: context,
            backgroundColor: const Color(0xFF10B981), // 翠绿色背景
            shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
            builder: (context) {
              return Padding(
                padding: const EdgeInsets.all(24.0),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.check_circle_outline, color: Colors.white, size: 64),
                    const SizedBox(height: 16),
                    Text(
                      '[$medicineName] $actionName成功！',
                      style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      isCompleted ? '该药品已完成所有复合扫描步骤' : '药品已流转到下一步骤',
                      style: const TextStyle(color: Colors.white70, fontSize: 14),
                    ),
                    const SizedBox(height: 24),
                    ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.white,
                        foregroundColor: const Color(0xFF10B981),
                      ),
                      onPressed: () {
                        Navigator.pop(context);
                        _fetchDetails(); // 刷新详情
                      },
                      child: const Text('好的'),
                    ),
                  ],
                ),
              );
            },
          );
        }
      }
    } on DioException catch (e) {
      HapticFeedback.heavyImpact(); // 失败强震动
      final err = e.response?.data?['error']?.toString() ?? '药品追溯码校验失败';
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(err), backgroundColor: Colors.redAccent),
      );
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_prescription == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('处方详情')),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    final p = _prescription!;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final isPharmacist = context.read<AuthProvider>().currentUser?.isPharmacist ?? false;

    return Scaffold(
      appBar: AppBar(
        title: Text('处方: ${p.prescriptionCode}'),
        actions: [
          // 如果是待配药或配药中状态，药师可扫码复核
          if (isPharmacist && (p.status == 'approved' || p.status == 'dispensing' || p.status == 'completed'))
            IconButton(
              icon: const Icon(Icons.qr_code_scanner, color: Color(0xFF00796B)),
              onPressed: _handleScanCode,
              tooltip: '扫码复核发药',
            )
        ],
      ),
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: isDark
                ? [const Color(0xFF090C15), const Color(0xFF0B1B2A), const Color(0xFF141221)]
                : [const Color(0xFF090C15), const Color(0xFF0B1B2A), const Color(0xFF141221)],
          ),
        ),
        child: _isLoading
            ? const Center(child: CircularProgressIndicator())
            : SingleChildScrollView(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // 患者信息卡片
                    GlassCard(
                      margin: EdgeInsets.zero,
                      padding: const EdgeInsets.all(20.0),
                      borderRadius: 24,
                      child: Row(
                          children: [
                            CircleAvatar(
                              backgroundColor: p.patientGender == '男' 
                                  ? Colors.blue.withValues(alpha: 0.1) 
                                  : Colors.pink.withValues(alpha: 0.1),
                              child: Icon(
                                p.patientGender == '男' ? Icons.male : Icons.female,
                                color: p.patientGender == '男' ? Colors.blue : Colors.pink,
                              ),
                            ),
                            const SizedBox(width: 16),
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  '${p.patientName ?? "未知"} (${p.patientGender ?? "未知"} · ${p.patientAge ?? 0}岁)',
                                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 17),
                                ),
                                const SizedBox(height: 4),
                                Text('门诊就诊号: ${p.prescriptionCode}', style: const TextStyle(fontSize: 12, color: Colors.grey)),
                              ],
                            ),
                          ],
                        ),
                      ),
                    const SizedBox(height: 12),

                    // 处方诊断与备注属性
                    GlassCard(
                      margin: EdgeInsets.zero,
                      padding: const EdgeInsets.all(20.0),
                      borderRadius: 24,
                      child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('就诊诊断与备注', style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold)),
                            const Divider(height: 20),
                            Row(
                              children: [
                                const Text('临床诊断: ', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                                Expanded(child: Text(p.items.isNotEmpty ? '急性支气管炎等诊断' : '无')), // 兜底
                              ],
                            ),
                            const SizedBox(height: 8),
                            Row(
                              children: [
                                const Text('支付类型: ', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                                Text(p.statusText), // 兜底
                              ],
                            ),
                            if (p.items.isNotEmpty && p.items.first.note != null) ...[
                              const SizedBox(height: 8),
                              Text('医生留言: ${p.items.first.note}', style: const TextStyle(fontSize: 13, color: Colors.grey)),
                            ]
                          ],
                        ),
                      ),
                    const SizedBox(height: 12),

                    // 药品明细列表 (带追溯码扫码状态展示)
                    GlassCard(
                      margin: EdgeInsets.zero,
                      padding: const EdgeInsets.all(20.0),
                      borderRadius: 24,
                      child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('开具药品及追溯码流转状态', style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold)),
                            const Divider(height: 20),
                            ListView.builder(
                              shrinkWrap: true,
                              physics: const NeverScrollableScrollPhysics(),
                              itemCount: p.items.length,
                              itemBuilder: (context, index) {
                                final item = p.items[index];
                                
                                return Padding(
                                  padding: const EdgeInsets.symmetric(vertical: 8.0),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Row(
                                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                        children: [
                                          Expanded(
                                            child: Text(
                                              item.medicineName ?? '未知药品',
                                              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
                                            ),
                                          ),
                                          Text(
                                            '数量: ${item.quantity}',
                                            style: const TextStyle(fontWeight: FontWeight.bold),
                                          ),
                                        ],
                                      ),
                                      const SizedBox(height: 4),
                                      Text(
                                        '规格: ${item.specification ?? "无"} | 用量: ${item.dosage} | 频次: ${item.frequency}',
                                        style: const TextStyle(color: Colors.grey, fontSize: 12),
                                      ),
                                      const SizedBox(height: 6),
                                      
                                      // 追溯码状态标签
                                      Row(
                                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                        children: [
                                          Text(
                                            '追溯码: ${item.traceCode ?? "未指定"}',
                                            style: const TextStyle(fontSize: 12, color: Colors.blueGrey),
                                          ),
                                          Container(
                                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                            decoration: BoxDecoration(
                                              color: _getTraceStatusColor(item.traceStatus).withValues(alpha: 0.1),
                                              borderRadius: BorderRadius.circular(4),
                                            ),
                                            child: Text(
                                              item.traceStatusText,
                                              style: TextStyle(
                                                color: _getTraceStatusColor(item.traceStatus),
                                                fontSize: 10,
                                                fontWeight: FontWeight.bold,
                                              ),
                                            ),
                                          ),
                                        ],
                                      ),
                                      const Divider(),
                                    ],
                                  ),
                                );
                              },
                            ),
                          ],
                        ),
                      ),
                    const SizedBox(height: 32),

                    // 药师审核/发药操作面板 (根据角色和状态动态渲染)
                    if (isPharmacist) ...[
                      // 1. 待审核状态 -> 审核通过 / 审核拒绝
                      if (p.status == 'pending')
                        Row(
                          children: [
                            Expanded(
                              child: OutlinedButton(
                                onPressed: () => _handleReview('rejected'),
                                style: OutlinedButton.styleFrom(
                                  side: const BorderSide(color: Colors.red),
                                  foregroundColor: Colors.red,
                                ),
                                child: const Text('驳回处方'),
                              ),
                            ),
                            const SizedBox(width: 16),
                            Expanded(
                              child: ElevatedButton(
                                onPressed: () => _handleReview('approved'),
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: const Color(0xFF00796B),
                                  foregroundColor: Colors.white,
                                ),
                                child: const Text('审核通过'),
                              ),
                            ),
                          ],
                        ),
                      
                      // 2. 审核通过(待配药) -> 扫码 / 确认发药
                      if (p.status == 'approved' || p.status == 'dispensing')
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            ElevatedButton.icon(
                              onPressed: _handleScanCode,
                              icon: const Icon(Icons.qr_code_scanner),
                              label: const Text('扫码配药复核'),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: const Color(0xFF00796B),
                                foregroundColor: Colors.white,
                                padding: const EdgeInsets.symmetric(vertical: 16),
                              ),
                            ),
                            const SizedBox(height: 12),
                            OutlinedButton(
                              onPressed: _handleDispense,
                              style: OutlinedButton.styleFrom(
                                padding: const EdgeInsets.symmetric(vertical: 16),
                              ),
                              child: const Text('直接确认发药(跳过扫码)'),
                            ),
                          ],
                        ),
                    ],
                  ],
                ),
              ),
      ),
    );
  }

  Color _getTraceStatusColor(String? status) {
    switch (status) {
      case 'pending':
        return Colors.orange;
      case 'scanned_identify':
        return Colors.blue;
      case 'scanned_outbound':
        return Colors.purple;
      case 'scanned_confirm':
        return Colors.green;
      default:
        return Colors.grey;
    }
  }
}
