import 'dart:async';
import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:his_mobile/core/network/api_client.dart';
import 'package:his_mobile/providers/auth_provider.dart';
import 'package:his_mobile/data/models/prescription_model.dart';
import 'package:his_mobile/views/patient/patient_list_page.dart';
import 'package:his_mobile/views/medicine/medicine_list_page.dart';
import 'package:his_mobile/views/prescription/prescription_list_page.dart';
import 'package:his_mobile/views/prescription/prescription_create_page.dart';
import 'package:his_mobile/views/prescription/prescription_detail_page.dart';
import 'package:his_mobile/core/theme/glass_card.dart';
import 'package:his_mobile/core/widgets/animated_scale_button.dart';

class HomeWorkbench extends StatefulWidget {
  const HomeWorkbench({super.key});

  @override
  State<HomeWorkbench> createState() => _HomeWorkbenchState();
}

class _HomeWorkbenchState extends State<HomeWorkbench> {
  int _currentIndex = 0;

  // 定时更新顶部时间
  late Timer _timeTimer;
  String _timeString = '';

  // 动态数据指标
  int _pendingPrescriptions = 0;
  int _totalMedicines = 0;
  int _totalPatients = 0;
  List<PrescriptionModel> _recentPrescriptions = [];
  bool _toolsExpanded = false;

  @override
  void initState() {
    super.initState();
    _updateTime();
    _timeTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (mounted) {
        _updateTime();
      }
    });
    // 获取实时看板数据
    _fetchStats();
  }

  @override
  void dispose() {
    _timeTimer.cancel();
    super.dispose();
  }

  void _updateTime() {
    final now = DateTime.now();
    setState(() {
      _timeString = '${now.year}-${now.month.toString().padLeft(2, '0')}-${now.day.toString().padLeft(2, '0')} '
          '${now.hour.toString().padLeft(2, '0')}:${now.minute.toString().padLeft(2, '0')}:${now.second.toString().padLeft(2, '0')}';
    });
  }

  // 从后端获取待审核处方数、药品数、病人总数，以及最新处方列表
  Future<void> _fetchStats() async {
    try {
      final dio = ApiClient().dio;
      // 1. 待审核处方
      final resPres = await dio.get('/api/prescriptions', queryParameters: {'status': 'pending', 'pageSize': 1});
      // 2. 药品总类
      final resMed = await dio.get('/api/medicines', queryParameters: {'pageSize': 1});
      // 3. 在册病人
      final resPat = await dio.get('/api/patients', queryParameters: {'pageSize': 1});
      // 4. 最新处方列表
      final resRecent = await dio.get('/api/prescriptions', queryParameters: {'pageSize': 5});

      if (mounted) {
        final list = resRecent.data['list'] as List? ?? [];
        setState(() {
          _pendingPrescriptions = resPres.data['total'] as int? ?? 0;
          _totalMedicines = resMed.data['total'] as int? ?? 0;
          _totalPatients = resPat.data['total'] as int? ?? 0;
          _recentPrescriptions = list.map((p) => PrescriptionModel.fromJson(p as Map<String, dynamic>)).toList();
        });
      }
    } catch (_) {}
  }

  // 切换分区
  void _onTabTapped(int index) {
    setState(() {
      _currentIndex = index;
    });
    if (index == 0) {
      _fetchStats(); // 每次回到工作版刷新指标
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final user = auth.currentUser;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    if (user == null) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    // 根据 Tab 导航获取当前主界面
    Widget currentBody;
    switch (_currentIndex) {
      case 0:
        currentBody = _buildWorkbenchView(auth);
        break;
      case 1:
        currentBody = user.isDoctor || user.role == 'admin'
            ? const PrescriptionCreatePage()
            : _buildNoPermissionView('医生');
        break;
      case 2:
        currentBody = user.isPharmacist || user.role == 'admin'
            ? const PrescriptionListPage()
            : _buildNoPermissionView('药师');
        break;
      case 3:
        currentBody = user.isDoctor || user.role == 'admin'
            ? const PatientListPage()
            : _buildNoPermissionView('医生');
        break;
      case 4:
        currentBody = const MedicineListPage(); // 所有人可查看药品管理
        break;
      default:
        currentBody = _buildWorkbenchView(auth);
    }

    return Scaffold(
      extendBody: true, // 让页面流延到悬浮底栏下方
      body: Stack(
        children: [
          Positioned.fill(
            child: currentBody,
          ),
          // 悬浮式毛玻璃底栏
          Positioned(
            left: 20,
            right: 20,
            bottom: 24,
            child: _buildFloatingBottomBar(isDark),
          ),
        ],
      ),
    );
  }

  // 渲染苹果悬浮磨砂底栏
  Widget _buildFloatingBottomBar(bool isDark) {
    final List<Map<String, dynamic>> items = [
      {'icon': Icons.dashboard_outlined, 'activeIcon': Icons.dashboard_rounded, 'label': '工作台'},
      {'icon': Icons.note_add_outlined, 'activeIcon': Icons.note_add_rounded, 'label': '开具'},
      {'icon': Icons.fact_check_outlined, 'activeIcon': Icons.fact_check_rounded, 'label': '审核'},
      {'icon': Icons.people_outline_rounded, 'activeIcon': Icons.people_rounded, 'label': '病人'},
      {'icon': Icons.medication_outlined, 'activeIcon': Icons.medication_rounded, 'label': '药品'},
    ];

    return Container(
      decoration: BoxDecoration(
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: isDark ? 0.25 : 0.08),
            blurRadius: 24,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(28),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 18, sigmaY: 18),
          child: Container(
            height: 70,
            padding: const EdgeInsets.symmetric(horizontal: 12),
            decoration: BoxDecoration(
              color: isDark 
                  ? Colors.black.withValues(alpha: 0.6) 
                  : Colors.white.withValues(alpha: 0.75),
              borderRadius: BorderRadius.circular(28),
              border: Border.all(
                color: isDark 
                    ? Colors.white.withValues(alpha: 0.08) 
                    : Colors.white.withValues(alpha: 0.4),
                width: 1.0,
              ),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: List.generate(items.length, (index) {
                final isSelected = _currentIndex == index;
                final item = items[index];
                return Expanded(
                  child: AnimatedScaleButton(
                    onTap: () => _onTabTapped(index),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          isSelected ? item['activeIcon'] as IconData : item['icon'] as IconData,
                          color: isSelected 
                              ? const Color(0xFF00796B) 
                              : (isDark ? Colors.white60 : Colors.black45),
                          size: 24,
                        ),
                        const SizedBox(height: 4),
                        Text(
                          item['label'] as String,
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight: isSelected ? FontWeight.w900 : FontWeight.normal,
                            color: isSelected 
                                ? const Color(0xFF00796B) 
                                : (isDark ? Colors.white54 : Colors.black54),
                          ),
                        ),
                      ],
                    ),
                  ),
                );
              }),
            ),
          ),
        ),
      ),
    );
  }

  // 渲染 Tab 0: 工作版 (苹果极简极宽舒设计)
  Widget _buildWorkbenchView(AuthProvider auth) {
    final user = auth.currentUser!;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: isDark
              ? [const Color(0xFF090C15), const Color(0xFF0B1B2A), const Color(0xFF141221)]
              : [const Color(0xFFEAF6FF), const Color(0xFFEDFDF8), const Color(0xFFFFF2F7)],
        ),
      ),
      child: SafeArea(
        bottom: false, // 底部留空给悬浮底栏
        child: RefreshIndicator(
          onRefresh: _fetchStats,
          color: const Color(0xFF009688),
          child: CustomScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            slivers: [
              // 1. 顶部大标题 + 头像 (苹果风格宽敞头部)
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(20.0, 24.0, 20.0, 16.0),
                  child: Row(
                    children: [
                      CircleAvatar(
                        radius: 26,
                        backgroundColor: const Color(0xFF00796B),
                        child: Text(
                          user.realName.isNotEmpty ? user.realName.substring(0, 1) : '药',
                          style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
                        ),
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              '仁爱医院 HIS',
                              style: TextStyle(
                                fontSize: 22,
                                fontWeight: FontWeight.w900,
                                color: isDark ? Colors.white : const Color(0xFF004D40),
                                letterSpacing: 0.5,
                              ),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              '欢迎，${user.realName} (${user.role == 'doctor' ? '医生' : '药师'}) · $_timeString',
                              style: TextStyle(
                                fontSize: 12,
                                color: isDark ? Colors.white60 : Colors.black54,
                              ),
                            ),
                          ],
                        ),
                      ),
                      IconButton(
                        icon: const Icon(Icons.logout_rounded, color: Colors.redAccent),
                        onPressed: () => auth.logout(),
                        tooltip: '退出登录',
                      ),
                    ],
                  ),
                ),
              ),

              // 2. iOS 风格 Stats 看板 (待审核 / 药品 / 病人 整合)
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 8.0),
                  child: Row(
                    children: [
                      // 待审核 (大卡片)
                      Expanded(
                        flex: 5,
                        child: AnimatedScaleButton(
                          onTap: () => _onTabTapped(2),
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 16.0),
                            decoration: BoxDecoration(
                              color: isDark 
                                  ? const Color(0xFF1E3A3A).withValues(alpha: 0.7) 
                                  : const Color(0xFFE0F2F1).withValues(alpha: 0.7),
                              borderRadius: BorderRadius.circular(20),
                              border: Border.all(
                                color: isDark 
                                    ? const Color(0xFF00796B).withValues(alpha: 0.3) 
                                    : const Color(0xFF00796B).withValues(alpha: 0.15),
                                width: 1.0,
                              ),
                            ),
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      '$_pendingPrescriptions',
                                      style: TextStyle(
                                        fontSize: 32,
                                        fontWeight: FontWeight.w900,
                                        color: isDark ? const Color(0xFF4DB6AC) : const Color(0xFF00796B),
                                      ),
                                    ),
                                    const SizedBox(height: 2),
                                    Text(
                                      '待审核处方',
                                      style: TextStyle(
                                        color: isDark ? const Color(0xFF80CBC4) : const Color(0xFF00796B),
                                        fontSize: 11,
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                                  ],
                                ),
                                Icon(
                                  Icons.pending_actions_rounded,
                                  color: isDark ? const Color(0xFF4DB6AC) : const Color(0xFF00796B),
                                  size: 30,
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      // 药品与病人 (双卡)
                      Expanded(
                        flex: 6,
                        child: Row(
                          children: [
                            Expanded(
                              child: AnimatedScaleButton(
                                onTap: () => _onTabTapped(4),
                                child: GlassCard(
                                  margin: EdgeInsets.zero,
                                  padding: const EdgeInsets.all(12.0),
                                  borderRadius: 20,
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        '$_totalMedicines',
                                        style: const TextStyle(
                                          fontSize: 22,
                                          fontWeight: FontWeight.w900,
                                          color: Color(0xFF7B1FA2),
                                        ),
                                      ),
                                      const SizedBox(height: 2),
                                      const Text(
                                        '药品品类',
                                        style: TextStyle(color: Colors.grey, fontSize: 10, fontWeight: FontWeight.bold),
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: AnimatedScaleButton(
                                onTap: () => _onTabTapped(3),
                                child: GlassCard(
                                  margin: EdgeInsets.zero,
                                  padding: const EdgeInsets.all(12.0),
                                  borderRadius: 20,
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        '$_totalPatients',
                                        style: const TextStyle(
                                          fontSize: 22,
                                          fontWeight: FontWeight.w900,
                                          color: Color(0xFF0288D1),
                                        ),
                                      ),
                                      const SizedBox(height: 2),
                                      const Text(
                                        '在册病人',
                                        style: TextStyle(color: Colors.grey, fontSize: 10, fontWeight: FontWeight.bold),
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),

              // 3. 核心功能大药丸面板 (2列精美宽舒布局)
              SliverPadding(
                padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 16.0),
                sliver: SliverGrid(
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 2,
                    crossAxisSpacing: 16,
                    mainAxisSpacing: 16,
                    childAspectRatio: 1.22,
                  ),
                  delegate: SliverChildListDelegate([
                    _buildActionCard(
                      title: '药盒汇总',
                      subtitle: '药盒数据状态看板',
                      icon: Icons.all_inbox_rounded,
                      color: const Color(0xFF009688),
                      onTap: () => _onTabTapped(2),
                    ),
                    _buildActionCard(
                      title: '处方审核',
                      subtitle: '快捷扫码复核与配药',
                      icon: Icons.fact_check_rounded,
                      color: const Color(0xFF00796B),
                      onTap: () => _onTabTapped(2),
                    ),
                    _buildActionCard(
                      title: '病人管理',
                      subtitle: '患者列表与建档表单',
                      icon: Icons.assignment_ind_rounded,
                      color: const Color(0xFF0288D1),
                      onTap: () => _onTabTapped(3),
                    ),
                    _buildActionCard(
                      title: '药品管理',
                      subtitle: '药品规格与库存统计',
                      icon: Icons.grid_view_rounded,
                      color: const Color(0xFF7B1FA2),
                      onTap: () => _onTabTapped(4),
                    ),
                  ]),
                ),
              ),

              // 4. 更多辅助工具折叠抽屉
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 4.0),
                  child: GlassCard(
                    margin: EdgeInsets.zero,
                    padding: EdgeInsets.zero,
                    borderRadius: 20,
                    child: Theme(
                      data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
                      child: ExpansionTile(
                        title: Text(
                          '更多临床与管理工具',
                          style: TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w800,
                            color: isDark ? Colors.white70 : Colors.black87,
                          ),
                        ),
                        leading: const Icon(Icons.apps_rounded, color: Colors.grey),
                        trailing: Icon(
                          _toolsExpanded ? Icons.keyboard_arrow_up_rounded : Icons.keyboard_arrow_down_rounded,
                          color: Colors.grey,
                        ),
                        onExpansionChanged: (expanded) {
                          setState(() {
                            _toolsExpanded = expanded;
                          });
                        },
                        children: [
                          Padding(
                            padding: const EdgeInsets.fromLTRB(16, 8, 16, 20),
                            child: GridView.count(
                              shrinkWrap: true,
                              physics: const NeverScrollableScrollPhysics(),
                              crossAxisCount: 4,
                              crossAxisSpacing: 10,
                              mainAxisSpacing: 16,
                              childAspectRatio: 0.9,
                              children: [
                                _buildMinorTool('医院取药', Icons.local_hospital_outlined),
                                _buildMinorTool('报表生成', Icons.analytics_outlined),
                                _buildMinorTool('药盒设置', Icons.settings_suggest_outlined),
                                _buildMinorTool('销账管理', Icons.receipt_long_outlined),
                                _buildMinorTool('操作记录', Icons.history_outlined),
                                _buildMinorTool('药品下架', Icons.vertical_align_bottom_outlined),
                                _buildMinorTool('补药汇总', Icons.add_business_outlined),
                                _buildMinorTool('库存查询', Icons.search_outlined),
                              ],
                            ),
                          )
                        ],
                      ),
                    ),
                  ),
                ),
              ),

              // 5. 最近处方板块 (完全舒展开)
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(20.0, 28.0, 20.0, 10.0),
                  child: Row(
                    children: [
                      const Icon(Icons.history_edu_rounded, color: Color(0xFF00796B), size: 20),
                      const SizedBox(width: 8),
                      Text(
                        '最近处方',
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w900,
                          color: isDark ? Colors.white : const Color(0xFF1E293B),
                          letterSpacing: 0.5,
                        ),
                      ),
                    ],
                  ),
                ),
              ),

              SliverPadding(
                padding: const EdgeInsets.fromLTRB(20.0, 0, 20.0, 110.0), // 留空给悬浮底栏
                sliver: SliverToBoxAdapter(
                  child: _recentPrescriptions.isEmpty
                      ? const GlassCard(
                          margin: EdgeInsets.zero,
                          padding: EdgeInsets.all(28.0),
                          borderRadius: 20,
                          child: Center(
                            child: Text('暂无最新处方记录', style: TextStyle(color: Colors.grey, fontSize: 13)),
                          ),
                        )
                      : GlassCard(
                          margin: EdgeInsets.zero,
                          padding: const EdgeInsets.symmetric(vertical: 10),
                          borderRadius: 20,
                          child: ListView.separated(
                            shrinkWrap: true,
                            physics: const NeverScrollableScrollPhysics(),
                            itemCount: _recentPrescriptions.length,
                            separatorBuilder: (context, idx) => const Divider(height: 1, color: Colors.black12),
                            itemBuilder: (context, idx) {
                              final p = _recentPrescriptions[idx];
                              
                              // 状态对应的中文文本与颜色
                              String statusText = p.statusText;
                              Color statusColor = Colors.grey;
                              switch (p.status) {
                                case 'pending':
                                  statusColor = Colors.orange;
                                  break;
                                case 'approved':
                                  statusColor = Colors.blue;
                                  break;
                                case 'dispensing':
                                  statusColor = Colors.purple;
                                  break;
                                case 'completed':
                                  statusColor = Colors.green;
                                  break;
                                case 'rejected':
                                  statusColor = Colors.red;
                                  break;
                              }

                              return ListTile(
                                contentPadding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 8.0),
                                title: Row(
                                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                  children: [
                                    Text(
                                      '${p.patientName ?? "未知"} (${p.patientGender ?? "未知"} · ${p.patientAge ?? "未知"}岁)',
                                      style: TextStyle(
                                        fontWeight: FontWeight.w800, 
                                        fontSize: 14,
                                        color: isDark ? Colors.white : const Color(0xFF1E293B),
                                      ),
                                    ),
                                    Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                      decoration: BoxDecoration(
                                        color: statusColor.withValues(alpha: 0.1),
                                        borderRadius: BorderRadius.circular(8),
                                      ),
                                      child: Text(
                                        statusText,
                                        style: TextStyle(color: statusColor, fontSize: 10, fontWeight: FontWeight.bold),
                                      ),
                                    ),
                                  ],
                                ),
                                subtitle: Padding(
                                  padding: const EdgeInsets.only(top: 8.0),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        '处方编号: ${p.prescriptionCode}',
                                        style: const TextStyle(fontSize: 12, color: Colors.grey),
                                      ),
                                      const SizedBox(height: 4),
                                      Text(
                                        '临床诊断: ${p.diagnosis ?? "未录入"} | 医生: ${p.doctorName ?? "管理员"}',
                                        style: TextStyle(
                                          fontSize: 12, 
                                          color: isDark ? Colors.white60 : Colors.black54,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                                onTap: () {
                                  Navigator.push(
                                    context,
                                    MaterialPageRoute(
                                      builder: (context) => PrescriptionDetailPage(prescriptionId: p.id),
                                    ),
                                  ).then((_) => _fetchStats()); // 返回时自动刷新
                                },
                              );
                            },
                          ),
                        ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // 构建核心大功能卡片的方法
  Widget _buildActionCard({
    required String title,
    required String subtitle,
    required IconData icon,
    required Color color,
    required VoidCallback onTap,
  }) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return AnimatedScaleButton(
      onTap: onTap,
      child: GlassCard(
        margin: EdgeInsets.zero,
        padding: const EdgeInsets.all(16.0),
        borderRadius: 20,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.12),
                shape: BoxShape.circle,
              ),
              child: Icon(icon, color: color, size: 22),
            ),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w900,
                    color: isDark ? Colors.white : const Color(0xFF1E293B),
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  subtitle,
                  style: const TextStyle(fontSize: 10, color: Colors.grey),
                ),
              ],
            )
          ],
        ),
      ),
    );
  }

  // 构建未开放的次要功能
  Widget _buildMinorTool(String title, IconData icon) {
    return AnimatedScaleButton(
      onTap: () {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('该功能正在升级开发中，暂未开放'), duration: Duration(milliseconds: 800)),
        );
      },
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: Colors.grey.withValues(alpha: 0.08),
              shape: BoxShape.circle,
            ),
            child: const Icon(Icons.lock_outline_rounded, color: Colors.grey, size: 18),
          ),
          const SizedBox(height: 6),
          Text(
            title,
            style: const TextStyle(fontSize: 10, color: Colors.grey),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }

  // 渲染无权限占位视图
  Widget _buildNoPermissionView(String requiredRole) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: isDark 
              ? [const Color(0xFF090C15), const Color(0xFF0B1B2A), const Color(0xFF141221)]
              : [const Color(0xFFEAF6FF), Colors.white],
        ),
      ),
      child: Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.lock_outline, size: 64, color: Colors.red.withValues(alpha: 0.7)),
              const SizedBox(height: 16),
              const Text(
                '权限不足',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              Text(
                '该功能仅限 [$requiredRole] 角色的账户访问。',
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.grey),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
