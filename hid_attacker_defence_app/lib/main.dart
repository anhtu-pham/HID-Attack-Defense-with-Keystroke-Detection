import 'dart:convert';
import 'dart:io';
import 'dart:async';

import 'dart:developer';
import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:tray_manager/tray_manager.dart';
import 'package:awesome_notifications/awesome_notifications.dart';
import 'package:window_manager/window_manager.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await AwesomeNotifications().initialize(null, [
    NotificationChannel(
      channelKey: 'alerts',
      channelName: 'Security Alerts',
      channelDescription: 'Notification channel for HID alerts',
    )
  ]);
  runApp(MyApp());
}

class MyApp extends StatefulWidget {
  @override
  State<MyApp> createState() => _MyAppState();
}

class _MyAppState extends State<MyApp> with TrayListener {
  List<String> logs = [];
  bool isRunning = false;
  Process? keystrokeProcess;
  Process? knnProcess;
  Process? blacklistProcess;
  List<FlSpot> keyData = [];
  int keyIndex = 0;
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
    startMonitoring();

    timer = Timer.periodic(Duration(seconds: 1), (_) {
      setState(() {
        keyData.add(FlSpot(keyIndex.toDouble(), currentSecondKeyCount.toDouble()));
        if (keyData.length > 60) keyData.removeAt(0);
        keyIndex++;
        currentSecondKeyCount = 0;
      });
    });
  }


  void startMonitoring() async {
    setState(() => isRunning = true);

    try {
      keystrokeProcess = await Process.start('python', ['../keystroke_detection.py']);
      _listenToLogs(keystrokeProcess!, 'Keystroke Monitor');
    } catch (e) {
      _logError('Failed to start keystroke_monitor.py: $e');
    }

    // try {
    //   knnProcess = await Process.start('python', ['../ML_model.py']);
    //   _listenToLogs(knnProcess!, 'KNN Model');
    // } catch (e) {
    //   _logError('Failed to start knn_model.py: $e');
    // }
    //
    // try {g
    //   blacklistProcess = await Process.start('python', ['../blacklist_linux.py']);
    //   _listenToLogs(blacklistProcess!, 'Blacklist Monitor');
    // } catch (e) {
    //   _logError('Failed to start blacklist.py: $e');
    // }
  }


  void _listenToLogs(Process process, String source) {
    process.stdout.transform(utf8.decoder).transform(LineSplitter()).listen((line) {
      if (!mounted) return;
      bool isKeystroke = line.contains("Key:") || RegExp(r"[a-zA-Z]'?").hasMatch(line);

      if (isKeystroke) {
        setState(() {
          totalKeystrokes++;
          currentSecondKeyCount++;
        });
      }

      if (line.toLowerCase().contains("suspicious") && line.toLowerCase().contains("detected")) {
        suspiciousCount++;
        _showAlert("Possible HID attack detected by $source!");
      }

      setState(() {
        logs.insert(0, "[$source] $line");
        if (logs.length > 500) logs.removeLast();
      });
    }, onError: (error) {
      _logError('Error reading logs from $source: $error');
    });

    process.stderr.transform(utf8.decoder).transform(LineSplitter()).listen((line) {
      _logError('[$source STDERR] $line');
    });
  }

  void _logError(String message) {
    if (!mounted) return;
    setState(() {
      logs.insert(0, message);
    });
  }

  void _showAlert(String message) {
    AwesomeNotifications().createNotification(
      content: NotificationContent(
        id: DateTime.now().millisecondsSinceEpoch.remainder(100000),
        channelKey: 'alerts',
        title: '🚨 HID Attack Alert',
        body: message,
      ),
    );
  }

  @override
  void dispose() {
    timer?.cancel();
    super.dispose();
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
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'HID Defense',
      home: Scaffold(
        appBar: AppBar(
          title: Text('🔐 HID-Attacker Defense System'),
          actions: [
            isRunning
                ? TextButton(
                onPressed: () {},
                child: Text("🟢 Running", style: TextStyle(color: Colors.white)))
                : TextButton(
                onPressed: startMonitoring,
                child: Text("Start", style: TextStyle(color: Colors.white)))
          ],
        ),
        body: Column(
          children: [
            Expanded(
              flex: 2,
              child: Container(
                padding: EdgeInsets.all(10),
                child: ListView.builder(
                  reverse: true,
                  itemCount: logs.length,
                  itemBuilder: (context, index) => Text(logs[index]),
                ),
              ),
            ),
            Divider(),
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 8.0),
              child: Column(
                children: [
                  Text("🔍 Keystroke Activity Per Second", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  Text("Total Keystrokes: $totalKeystrokes | Alerts: $suspiciousCount", style: TextStyle(color: Colors.grey[700]))
                ],
              ),
            ),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.all(0),
                child: LineChart(LineChartData(
                  minY: 0,
                  gridData: FlGridData(show: true, drawVerticalLine: true, horizontalInterval: 1, verticalInterval: 5),
                  titlesData: FlTitlesData(
                    leftTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        getTitlesWidget: (value, meta) => Text('${value.toInt()}', style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold)),
                        reservedSize: 28,
                      ),
                      axisNameWidget: Padding(
                        padding: EdgeInsets.only(bottom: 0),
                        child: Text("Keys/sec", style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold)),
                      ),
                      axisNameSize: 16,
                    ),
                    bottomTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        getTitlesWidget: (value, meta) => Text('${value.toInt()}s', style: TextStyle(fontSize: 10)),
                      ),
                      axisNameWidget: Padding(
                        padding: EdgeInsets.only(top: 0),
                        child: Text("Seconds", style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                      ),
                      axisNameSize: 16,
                    ),
                  ),
                  borderData: FlBorderData(show: true),
                  lineBarsData: [
                    LineChartBarData(
                      spots: keyData.isEmpty ? [FlSpot(0, 0)] : keyData,
                      isCurved: true,
                      barWidth: 3,
                      color: Colors.green,
                      belowBarData: BarAreaData(show: true, color: Colors.green.withOpacity(0.2)),
                    )
                  ],
                )),
              ),
            )
          ],
        ),
      ),
    );
  }
}
