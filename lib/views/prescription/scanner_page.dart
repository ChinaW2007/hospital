import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

class ScannerPage extends StatefulWidget {
  const ScannerPage({super.key});

  @override
  State<ScannerPage> createState() => _ScannerPageState();
}

class _ScannerPageState extends State<ScannerPage> with SingleTickerProviderStateMixin {
  final MobileScannerController _controller = MobileScannerController(
    detectionSpeed: DetectionSpeed.noDuplicates,
    facing: CameraFacing.back,
  );

  late AnimationController _animationController;
  bool _isFlashOn = false;

  @override
  void initState() {
    super.initState();
    // 初始化扫描线动画
    _animationController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _controller.dispose();
    _animationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        title: const Text('扫描药品追溯码'),
        backgroundColor: Colors.transparent,
        elevation: 0,
        actions: [
          IconButton(
            icon: Icon(_isFlashOn ? Icons.flash_on : Icons.flash_off, color: Colors.white),
            onPressed: () {
              _controller.toggleTorch();
              setState(() => _isFlashOn = !_isFlashOn);
            },
          ),
          IconButton(
            icon: const Icon(Icons.flip_camera_ios, color: Colors.white),
            onPressed: () => _controller.switchCamera(),
          ),
        ],
      ),
      backgroundColor: Colors.black,
      body: Stack(
        children: [
          // 1. 扫码取景器
          MobileScanner(
            controller: _controller,
            onDetect: (capture) {
              final List<Barcode> barcodes = capture.barcodes;
              if (barcodes.isNotEmpty) {
                final String? code = barcodes.first.rawValue;
                if (code != null && code.isNotEmpty) {
                  Navigator.pop(context, code);
                }
              }
            },
          ),

          // 2. 黑色半透明遮罩 (中空效果)
          const ScannerOverlay(),

          // 3. 扫描框内容 (边框和动画线)
          Center(
            child: SizedBox(
              width: 280,
              height: 280,
              child: Stack(
                children: [
                  // 四个角的边框
                  const ScannerBorder(),
                  
                  // 动态扫描线
                  AnimatedBuilder(
                    animation: _animationController,
                    builder: (context, child) {
                      return Positioned(
                        top: 10 + (260 * _animationController.value),
                        left: 20,
                        right: 20,
                        child: Container(
                          height: 2,
                          decoration: BoxDecoration(
                            boxShadow: [
                              BoxShadow(
                                color: Colors.blue.withOpacity(0.5),
                                blurRadius: 4,
                                spreadRadius: 2,
                              )
                            ],
                            gradient: const LinearGradient(
                              colors: [
                                Colors.transparent,
                                Colors.blueAccent,
                                Colors.transparent,
                              ],
                            ),
                          ),
                        ),
                      );
                    },
                  ),
                ],
              ),
            ),
          ),

          // 4. 底部文字提示
          Positioned(
            bottom: 100,
            left: 0,
            right: 0,
            child: Column(
              children: [
                const Text(
                  '请将条形码/二维码置于框内',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 16,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  '支持扫描药品追溯码',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.7),
                    fontSize: 14,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// 绘制四周遮罩层
class ScannerOverlay extends StatelessWidget {
  const ScannerOverlay({super.key});

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(builder: (context, constraints) {
      double width = 280;
      double height = 280;
      double top = (constraints.maxHeight - height) / 2;
      double left = (constraints.maxWidth - width) / 2;

      return Stack(
        children: [
          // 上遮罩
          Positioned(top: 0, left: 0, right: 0, height: top, child: Container(color: Colors.black54)),
          // 下遮罩
          Positioned(top: top + height, left: 0, right: 0, bottom: 0, child: Container(color: Colors.black54)),
          // 左遮罩
          Positioned(top: top, left: 0, width: left, height: height, child: Container(color: Colors.black54)),
          // 右遮罩
          Positioned(top: top, left: left + width, right: 0, height: height, child: Container(color: Colors.black54)),
        ],
      );
    });
  }
}

/// 绘制扫描框的四个角
class ScannerBorder extends StatelessWidget {
  const ScannerBorder({super.key});

  @override
  Widget build(BuildContext context) {
    const double borderSize = 25.0;
    const double thickness = 4.0;
    const Color borderColor = Colors.blueAccent;

    return Stack(
      children: [
        // 左上角
        Positioned(
          top: 0,
          left: 0,
          child: Container(
            width: borderSize,
            height: thickness,
            decoration: const BoxDecoration(color: borderColor, borderRadius: BorderRadius.all(Radius.circular(2))),
          ),
        ),
        Positioned(
          top: 0,
          left: 0,
          child: Container(
            width: thickness,
            height: borderSize,
            decoration: const BoxDecoration(color: borderColor, borderRadius: BorderRadius.all(Radius.circular(2))),
          ),
        ),
        // 右上角
        Positioned(
          top: 0,
          right: 0,
          child: Container(
            width: borderSize,
            height: thickness,
            decoration: const BoxDecoration(color: borderColor, borderRadius: BorderRadius.all(Radius.circular(2))),
          ),
        ),
        Positioned(
          top: 0,
          right: 0,
          child: Container(
            width: thickness,
            height: borderSize,
            decoration: const BoxDecoration(color: borderColor, borderRadius: BorderRadius.all(Radius.circular(2))),
          ),
        ),
        // 左下角
        Positioned(
          bottom: 0,
          left: 0,
          child: Container(
            width: borderSize,
            height: thickness,
            decoration: const BoxDecoration(color: borderColor, borderRadius: BorderRadius.all(Radius.circular(2))),
          ),
        ),
        Positioned(
          bottom: 0,
          left: 0,
          child: Container(
            width: thickness,
            height: borderSize,
            decoration: const BoxDecoration(color: borderColor, borderRadius: BorderRadius.all(Radius.circular(2))),
          ),
        ),
        // 右下角
        Positioned(
          bottom: 0,
          right: 0,
          child: Container(
            width: borderSize,
            height: thickness,
            decoration: const BoxDecoration(color: borderColor, borderRadius: BorderRadius.all(Radius.circular(2))),
          ),
        ),
        Positioned(
          bottom: 0,
          right: 0,
          child: Container(
            width: thickness,
            height: borderSize,
            decoration: const BoxDecoration(color: borderColor, borderRadius: BorderRadius.all(Radius.circular(2))),
          ),
        ),
      ],
    );
  }
}
