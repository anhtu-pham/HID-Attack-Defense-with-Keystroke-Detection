import 'dart:convert';
import 'dart:io';
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:tray_manager/tray_manager.dart';
import 'package:awesome_notifications/awesome_notifications.dart';
import 'package:window_manager/window_manager.dart';
import 'package:flutter/services.dart';

int safeLevel = 3;
const double window_width = 1200;
const double window_height = 1000;

bool monitor_error = false;
void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await windowManager.ensureInitialized();
  await windowManager.setMinimumSize(const Size(window_width, window_height));
  await windowManager.setMaximumSize(const Size(window_width, window_height));
  await windowManager.setSize(const Size(window_width, window_height));
  await windowManager.setResizable(false);
  await windowManager.center();
  await windowManager.show();
  await AwesomeNotifications().initialize(null, [
    NotificationChannel(
      channelKey: 'alerts',
      channelName: 'Security Alerts',
      channelDescription: 'Notification channel for HID alerts',
    )
  ]);
  runApp(MyApp());
}

void showWindowsPopup(String title, String message) async {
  final script = '''
  [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > \$null
  \$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
  \$textNodes = \$template.GetElementsByTagName("text")
  \$textNodes.Item(0).AppendChild(\$template.CreateTextNode("$title")) > \$null
  \$textNodes.Item(1).AppendChild(\$template.CreateTextNode("$message")) > \$null
  \$toast = [Windows.UI.Notifications.ToastNotification]::new(\$template)
  \$notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("HID Defense")
  \$notifier.Show(\$toast)
  ''';

  await Process.start('powershell', ['-Command', script]);
}
class MyApp extends StatefulWidget {
  @override
  State<MyApp> createState() => _MyAppState();
}

class _MyAppState extends State<MyApp> with TrayListener {
  List<String> logs = [];
  bool isRunning = false;
  Process? keystrokeProcess;
  Timer? monitorTimer;
  Process? knnProcess;
  Process? blacklistProcess;
  List<int> keyCounts = List.generate(60, (_) => 0); // Growable list with 60 zeros
  int totalKeystrokes = 0;
  int suspiciousCount = 0;
  int currentSecondKeyCount = 0;
  Timer? timer;

  @override
  void initState() {
    super.initState();
    trayManager.addListener(this);
    trayManager.setIcon('assets/icon.png');
    trayManager.setContextMenu(Menu(items: [
      MenuItem(key: 'show', label: 'Show'),
      MenuItem(key: 'exit', label: 'Exit')
    ]));

    // Shift data every second
    timer = Timer.periodic(Duration(seconds: 1), (Timer t) {
      try {
        setState(() {
          keyCounts.removeAt(0);
          keyCounts.add(currentSecondKeyCount);
          currentSecondKeyCount = 0;
        });
      } catch (e, stack) {

      _logError('Timer error: $e\n$stack');
    }
    });

    startMonitoring();
  }
  void stopMonitoring() {
    setState(() => isRunning = false);

    keystrokeProcess?.kill();
    knnProcess?.kill();
    blacklistProcess?.kill();
  }
  void startMonitoring() async {
    setState(() => isRunning = true);

    try {
      keystrokeProcess = await Process.start('python', ['../keystroke_detection_polling.py']);
      _listenToLogs(keystrokeProcess!, 'Keystroke Monitor Status');
    } catch (e) {
      _logError('Failed to start keystroke_monitor.py: $e');
    }
  }

  void _startProcessMonitor() {
    monitorTimer?.cancel(); // ensure no duplicate timers

    monitorTimer = Timer.periodic(Duration(seconds: 3), (_) async {
      if (keystrokeProcess == null) return;

      // Check if process is still alive
      final exited = await keystrokeProcess!.exitCode.catchError((_) => null);
      if (exited != null && isRunning) {
        _logError("🔁 Keystroke script stopped. Restarting...");
        startMonitoring(); // restart the process
      }
    });
  }

  void _listenToLogs(Process process, String source) {
    process.stdout.transform(utf8.decoder).transform(LineSplitter()).listen((line) {
      if (!mounted) return;
      // Remove "INFO:root:" prefix if present
      line = line.replaceFirst(RegExp(r'^INFO:root:\s*'), '');
      if (line.contains('Key') && line.contains('Timestamp')) {
        try {
          final decoded = json.decode(line);
          if (decoded is Map && decoded.containsKey("Key") && decoded.containsKey("Timestamp")) {
            final rawKey = decoded["Key"].toString().replaceAll("'", "").replaceAll("{", "").replaceAll("}", "").trim();
            final key = rawKey.isEmpty ? "[Unknown]" : rawKey;
            final ts = DateTime.fromMillisecondsSinceEpoch(decoded["Timestamp"]);
            final formattedTime = "${ts.year}-${ts.month.toString().padLeft(2, '0')}-${ts.day.toString().padLeft(2, '0')} "
                "${ts.hour.toString().padLeft(2, '0')}:${ts.minute.toString().padLeft(2, '0')}:${ts.second.toString().padLeft(2, '0')}";

            setState(() {
              totalKeystrokes++;
              currentSecondKeyCount++;
              logs.insert(0, "🕒 [$formattedTime]: ⌨️ Key Pressed: $key");
              if (logs.length > 500) logs.removeLast();
            });
            return;
          }
        } catch (e) {
          // Log failed JSON parse with original line
          setState(() {
            logs.insert(0, "⚠️ Failed to parse JSON from $source: \"$line\" | Error: $e");
            if (logs.length > 500) logs.removeLast();
          });
        }
      }

      if (line.toLowerCase().contains("suspicious behavior is not yet detected")) {
        safeLevel = 3;
      }else
      if (line.toLowerCase().contains("suspicious behavior is detected")) {
        suspiciousCount++;

        if(safeLevel != 2) {
          SystemSound.play(SystemSoundType.alert); // Native alert sound
          safeLevel = 2;
        }
      }else
      // Fallback for suspicious or plain text logs
      if (line.toLowerCase().contains("hid attack is detected")) {

        _showAlert("Possible HID attack detected by $source!");
      }

      logs.insert(0, "[$source] $line");

    }, onError: (error) {
      _logError('Error reading logs from $source: $error');
    });

    process.stderr.transform(utf8.decoder).transform(LineSplitter()).listen((line) {
      _logError('[$source STDERR] $line');
    });
  }

  void _logError(String message) {
    monitor_error = true;
    if (!mounted) return;
    setState(() {
      logs.insert(0, message);
    });
  }

  void _showAlert(String message) {
    setState(() {
      safeLevel = 1;
    });

    SystemSound.play(SystemSoundType.alert); // Native alert sound
    showWindowsPopup("HID Attack Detected", message); //Native toast

    AwesomeNotifications().createNotification(
      content: NotificationContent(
        id: DateTime.now().millisecondsSinceEpoch.remainder(100000),
        channelKey: 'alerts',
        title: '🚨 HID Attack Alert',
        body: message,
      ),
    );

    // Windows alert sound
    SystemSound.play(SystemSoundType.alert);
  }



  @override
  void onTrayIconMouseDown() {
    trayManager.popUpContextMenu();
  }

  @override
  void onTrayMenuItemClick(MenuItem menuItem) async {
    if (menuItem.key == 'show') {
      await windowManager.show();
      await windowManager.focus();
    } else if (menuItem.key == 'exit') {
      exit(0);
    }
  }


  @override
  Widget build(BuildContext context) {
    final spots = keyCounts.asMap().entries.map((e) => FlSpot(e.key.toDouble(), e.value.toDouble())).toList();
    final maxY = (keyCounts.reduce((a, b) => a > b ? a : b) + 1).toDouble();

    return MaterialApp(
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark(),
      title: 'HID Keystroke Monitor',
      home: Scaffold(
        appBar: AppBar(
          title: Stack(
            children: [
              Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  '🔐 HID-Keystroke Monitor',
                  style: TextStyle(fontSize: 18),
                ),
              ),
              Align(
              alignment: Alignment.center,
              child: Container(
                decoration: BoxDecoration(
                  color: Colors.grey[800], // static gray background
                  borderRadius: BorderRadius.circular(10),
                ),
                padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                child: TextButton(
                  onPressed: isRunning ? stopMonitoring : startMonitoring,
                  style: TextButton.styleFrom(
                    minimumSize: Size(120, 40),
                    padding: EdgeInsets.zero,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
                    alignment: Alignment.center,
                  ),
                  child: Text(
                    isRunning ?   '🟢 Running  ' : '▶️ Start',
                    style: TextStyle(
                      color: isRunning ? Colors.green : Colors.grey,
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                    textAlign: TextAlign.center,
                  ),
                ),
              ),
            ),
            ],
          ),
          automaticallyImplyLeading: false,
        ),
        body: Column(
          children: [
            Expanded(
              flex: 2,
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    flex: 4,
                    child: Container(
                      padding: EdgeInsets.all(10),
                      child: ListView.builder(
                        reverse: true,
                        itemCount: logs.length,
                        itemBuilder: (context, index) {
                          final log = logs[index];
                          final isKeystrokeLog = log.contains("Key Pressed:") || log.contains("⌨️");
                          monitor_error =  !log.toLowerCase().contains("suspicious") && !log.toLowerCase().contains("continue") && !log.toLowerCase().contains("starting") && !isKeystrokeLog;
                          return Text(
                            log,
                            style: TextStyle(
                              color: monitor_error? Colors.red : isKeystrokeLog ? Colors.white : Colors.greenAccent,
                              fontFamily: 'Courier', // optional: makes logs look like terminal
                            ),
                          );
                        },
                      ),
                    ),
                  ),
                  Container(
                    width: 250,
                    margin: EdgeInsets.all(12),
                    padding: EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: safeLevel ==3 ? Colors.green : (safeLevel == 2)? Colors.yellow : Colors.red,
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: Colors.white, width:  4),
                    ),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          safeLevel == 3 ? Icons.check_circle : safeLevel ==2 ? Icons.warning : Icons.error,
                          size: 80,
                          color: Colors.white,
                        ),
                        SizedBox(height: 10),
                        Text(
                          safeLevel == 3 ? 'NO ATTACKER' : safeLevel == 2? 'SUSPICIOUS BEHAVIOR':'ATTACKER DETECTED' ,
                          style: TextStyle(
                            fontSize: 19,
                            fontWeight: FontWeight.bold,
                            color: Colors.white,
                          ),
                        ),
                      ],
                    ),
                  )
                ],
              ),
            ),
            Divider(color: Colors.grey),
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 8.0),
              child: Column(
                children: [
                  Text('🔍 Keystroke Activity (0–60s)', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white)),
                  Text('Total Keystrokes: $totalKeystrokes | Alerts: $suspiciousCount', style: TextStyle(color: Colors.grey[300])),
                ],
              ),
            ),
            Expanded(
              flex: 2,
              child: Padding(
                padding: const EdgeInsets.all(12.0),
                child: LineChart(
                  LineChartData(
                    backgroundColor: Colors.black,
                    minY: -0.02,
                    maxY: maxY,
                    minX: 0,
                    maxX: 59,
                    clipData: FlClipData.all(), // this ensures the curve doesn't draw below minY
                    gridData: FlGridData(
                      show: true,
                      drawVerticalLine: true,
                      getDrawingHorizontalLine: (v) => FlLine(color: Colors.grey[800]!, strokeWidth: 1),
                      getDrawingVerticalLine: (v) => FlLine(color: Colors.grey[800]!, strokeWidth: 1),
                    ),
                    titlesData: FlTitlesData(
                      topTitles: AxisTitles(
                        sideTitles: SideTitles(showTitles: false),
                      ),
                      rightTitles: AxisTitles(
                        sideTitles: SideTitles(showTitles: false),
                      ),
                      leftTitles: AxisTitles(
                        sideTitles: SideTitles(
                          showTitles: true,
                          getTitlesWidget: (val, meta) => Text('${val.toInt()}', style: TextStyle(color: Colors.cyanAccent, fontSize: 10)),
                          reservedSize: 20,
                        ),
                        axisNameWidget: Padding(
                          padding: EdgeInsets.only(bottom: 0),
                          child: Text('Keys/sec', style: TextStyle(color: Colors.cyanAccent, fontSize: 12)),
                        ),
                      ),
                      bottomTitles: AxisTitles(
                        sideTitles: SideTitles(
                          showTitles: true,
                          interval: 5,
                          getTitlesWidget: (val, meta) => Text('${val.toInt()}s', style: TextStyle(color: Colors.amberAccent, fontSize: 10)),
                        ),
                        axisNameWidget: Padding(
                          padding: EdgeInsets.only(top: 0),
                          child: Text('Seconds', style: TextStyle(color: Colors.amberAccent, fontSize: 12)),
                        ),
                      ),
                    ),
                    borderData: FlBorderData(show: true, border: Border.all(color: Colors.grey[700]!)),
                    lineBarsData: [
                      LineChartBarData(
                        spots: spots,
                        isCurved: true,
                        curveSmoothness: 0.2, // Optional: control curvature (0 = tight, 1 = loose)
                        barWidth: 2,
                        dotData: FlDotData(
                          show: true, // Show dots
                          getDotPainter: (spot, percent, barData, index) => FlDotCirclePainter(
                            radius: 3,
                            color: Colors.greenAccent,
                            strokeColor: Colors.black,
                          ),
                        ),
                        belowBarData: BarAreaData(show: true, color: Colors.green.withOpacity(0.2)),
                        gradient: LinearGradient(
                          colors: [Colors.greenAccent, Colors.lightGreenAccent],
                        ),
                      )
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
