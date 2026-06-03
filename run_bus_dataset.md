# SVIn 运行 Bus 数据集指南

## 一键运行指令

```bash
# ===== 终端 1: 启动 SVIn =====
source /opt/ros/humble/setup.bash
source /home/zhuchao/svin_ws/install/setup.bash
ros2 launch okvis_ros svin_stereorig_v1.xml

# ===== 终端 2: 播放数据集 (等终端1 RViz窗口出现后执行) =====
source /opt/ros/humble/setup.bash
ros2 bag play /home/zhuchao/svin_ws/date_record/bus_outside.db3 --clock

# ===== 结束后 Ctrl+C 终端1 保存轨迹 =====
```

## 运行其他数据集

```bash
# Cave 数据集 (终端2改为 cave_gennie.db3)
ros2 launch okvis_ros svin_stereorig_v2.xml

# Cemetery 数据集 (终端2改为 cemetery.db3)
ros2 launch okvis_ros svin_stereorig_v1.xml

# GoPro 水下数据集
ros2 launch okvis_ros svin_gopro_uw.xml
```

## 输出结果

轨迹和点云保存在: `src/SVIn/pose_graph/svin_results/`

---

# SVIn 配置文件体系说明

SVIn 由 **2 个模块** 组成，共用 **1 份配置文件**，通过 launch 文件将三部分串联：

```
Launch文件 (XML/Python)
  │
  ├─► stereo_sync 节点 ── 同步/解压/缩放图像
  ├─► okvis_node    ── VIO 前端 + Ceres 优化 (从config读取相机/IMU/检测参数)
  ├─► pose_graph    ── 回环检测 + 位姿图优化 (从config读取闭环/地图参数)
  └─► rviz2         ── 可视化
```

## 1. Launch 文件 — 选择运行场景

Launch 文件决定：**用什么config、传感器话题名、是否解压图像**。

| Launch 文件 | 适用场景 | 双目话题 | IMU话题 |
|------------|---------|---------|--------|
| `svin_stereorig_v1.xml` | AFRL Bus/Cemetery 数据集 | `/slave1/image_raw/compressed` | `/imu/imu` |
| `svin_stereorig_v2.xml` | AFRL Cave 数据集 | `/slave1/image_raw/compressed` | `/imu/imu` |
| `svin_zy_zed2i.launch.py` | 实时 ZED2i 相机 | `/zed/.../left/image` | `/imu_mFOSN` |
| `svin_gopro_uw.xml` | GoPro 水下数据集 | 直接订阅 `/cam0`,`/cam1` | `/imu` |

**适配自己的传感器需要修改的部分：**

```xml
<!-- ===== stereo_sync 节点: 双目图像输入 ===== -->
<param name="left_img_topic"  value="/你的左图话题"/>
<param name="right_img_topic" value="/你的右图话题"/>
<param name="compressed" value="true"/>   <!-- true=压缩图, false=原始图 -->

<!-- ===== okvis_node 话题映射 ===== -->
<remap from="/camera0" to="/cam0/image_raw"/>  <!-- 左图(经stereo_sync后) -->
<remap from="/camera1" to="/cam1/image_raw"/>  <!-- 右图(经stereo_sync后) -->
<remap from="/imu"     to="/你的IMU话题"/>
```

**不需要 stereo_sync**（图像已经是原始未压缩格式）：
- 去掉 `<node name="stereo_sync">` 整个块
- 将 okvis_node 中的 `/camera0`, `/camera1` 直接映射到传感器图像话题

## 2. Config YAML — 核心传感器参数

配置文件定义了 **相机内参/外参、IMU参数、特征检测、闭环、优化** 等所有算法参数。

配置文件位置: `config/config_<平台名>.yaml` (共 13 个预设配置)

### 2.1 相机参数 `cameras:`

```yaml
cameras:
    - T_SC:                    # 相机 → IMU/Sensor 的外参 (4x4变换矩阵，行优先)
       [r11, r12, r13, tx,
        r21, r22, r23, ty,
        r31, r32, r33, tz,
          0,   0,   0,  1]
      image_dimension: [宽, 高]  # 原始图像分辨率 (像素)
      distortion_coefficients: [k1, k2, p1, p2]  # radtan畸变系数
      distortion_type: radialtangential  # 畸变模型: radialtangential / equidistant / radialtangential8
      focal_length: [fx, fy]              # 焦距 (像素)
      principal_point: [cx, cy]           # 主点 (像素)

    - T_SC: ...  # 第二个相机（右目），结构同上
```

> **新传感器适配关键**: 标定得到的相机内参(fx,fy,cx,cy,k1,k2,p1,p2) 和外参(T_SC) 填到这里。

### 2.2 相机采集参数 `camera_params:`

```yaml
camera_params:
    camera_rate: 13                       # 相机帧率 (Hz)
    sigma_absolute_translation: 0.0       # 绝对位置约束的噪声
    sigma_absolute_orientation: 0.0       # 绝对姿态约束的噪声
    sigma_c_relative_translation: 0.0     # 相机间相对平移噪声
    sigma_c_relative_orientation: 0.0     # 相机间相对旋转噪声
```

### 2.3 IMU 参数 `imu_params:`

```yaml
imu_params:
    a_max: 176.0             # 加速度计量程 [m/s²]
    g_max: 7.8               # 陀螺仪量程 [rad/s]
    sigma_g_c: 0.0016017     # 陀螺仪噪声密度 [rad/s/√Hz]
    sigma_a_c: 0.0071376     # 加速度计噪声密度 [m/s²/√Hz]
    sigma_bg: 0.03           # 陀螺仪bias先验 [rad/s]
    sigma_ba: 0.1            # 加速度计bias先验 [m/s²]
    sigma_gw_c: 0.0000165    # 陀螺仪随机游走 [rad/s²/√Hz]
    sigma_aw_c: 0.0002874    # 加速度计随机游走 [m/s²²/√Hz]
    tau: 3600.0              # bias回归时间常数 [s]
    g: 9.81007               # 重力加速度 [m/s²]
    a0: [0.0, 0.0, 0.0]     # 加速度计初始bias [m/s²]
    imu_rate: 100            # IMU频率 [Hz]
    T_BS:                    # IMU → Body 外参 (4x4)
      [1,  0,  0, tx,
       0, -1,  0, ty,
       0,  0, -1, tz,
       0,  0,  0,  1]
```

> **新传感器适配关键**: 填入 IMU 数据手册中的噪声参数，以及标定得到的 IMU 到相机的外参 T_BS。

### 2.4 声纳参数 `sonar_params:` (水下场景)

```yaml
sonar_params:
    T_SSo:           # 声纳 → Sensor 外参
      [...]
isSonarUsed: false   # 是否启用声纳
isDepthUsed: false   # 是否启用深度计
```

### 2.5 图像预处理

```yaml
histogramMethod: "CLAHE"    # 直方图均衡方法: NONE / HISTOGRAM / CLAHE
claheClipLimit: 1.0         # CLAHE 对比度限制
claheTilesGridSize: 2       # CLAHE 网格大小
resizeFactor: 0.5           # 图像缩放因子 (0.5 = 1600x1200→800x600)
```

### 2.6 特征检测 `detection_options:`

```yaml
detection_options:
    threshold: 20.0          # BRISK 检测阈值 (越低越多特征点)
    octaves: 1               # 尺度空间octave数 (0=单尺度)
    maxNoKeypoints: 400      # 每帧最大特征点数
```

### 2.7 估计器参数

```yaml
numKeyframes: 5              # 优化窗口内关键帧数
numImuFrames: 3              # 非线性IMU误差项连接的帧数
imageDelay: 0.0              # 图像时间延迟 [s]

ceres_options:
    minIterations: 3         # Ceres 最小迭代次数
    maxIterations: 10        # Ceres 最大迭代次数
    timeLimit: 0.035         # 单次优化时间限制 [s]
```

### 2.8 回环检测参数 `loop_closure_params:`

```yaml
loop_closure_params:
    enable: 1                        # 启用回环检测 (0=禁用)
    min_correspondences: 25          # 最小2D-3D匹配数
    pnp_reprojection_threshold: 20.0 # PnP重投影阈值
    pnp_ransac_iterations: 100       # PnP RANSAC迭代次数
    keyframe_queue: 10               # 关键帧队列大小 (-1=不跳过)
    max_yaw_diff: 30.0               # 最大偏航角差 [度]
    max_position_diff: 6.0           # 最大位置差 [米]
```

### 2.9 输出参数

```yaml
output_params:
    debug: 0
    output_dir: ~/svin_ws/src/SVIn/pose_graph  # 轨迹输出目录
```

---

## 3. 适配自己的传感器 — 最小步骤

### 步骤 1: 标定传感器

获取以下数据：
- **双目相机**: 左右目内参 (fx,fy,cx,cy,k1,k2,p1,p2) + 双目外参 (T_left_right)
- **相机-IMU**: 外参 T_BS (IMU→Body) 和 T_SC (相机→IMU)
- **IMU**: 噪声密度、随机游走、量程（从数据手册）

### 步骤 2: 创建配置文件

```bash
cp config/config_stereorig_v1.yaml config/config_my_sensor.yaml
# 编辑 config_my_sensor.yaml:
#   1. cameras[0].T_SC: 填入你的左目→IMU外参
#   2. cameras[1].T_SC: 填入你的右目→IMU外参
#   3. focal_length, principal_point: 填入你的相机内参
#   4. distortion_coefficients: 填入你的畸变系数
#   5. image_dimension: 你的图像分辨率
#   6. imu_params: 填入你的IMU参数
#   7. imu_params.T_BS: IMU→Body外参
#   8. camera_params.camera_rate: 你的相机帧率
#   9. resizeFactor: 1.0 (如果不想缩放)
```

### 步骤 3: 创建 Launch 文件

```bash
cp okvis_ros/launch/svin_stereorig_v1.xml okvis_ros/launch/svin_my_sensor.xml
# 编辑:
#   1. config 路径改为 config_my_sensor.yaml
#   2. 修改 left_img_topic 和 right_img_topic 为你的话题名
#   3. 修改 /imu 重映射为你的IMU话题名
#   4. 如果图像是原始格式 (非压缩), 去掉 stereo_sync 节点
```

### 步骤 4: 编译并运行

```bash
cd ~/svin_ws
source /opt/ros/humble/setup.bash
colcon build
source install/setup.bash
ros2 launch okvis_ros svin_my_sensor.xml
```

---

## 4. 配置文件速查表

| 场景 | Launch 文件 | Config 文件 | Bag文件 | 特点 |
|------|-----------|------------|---------|------|
| **Bus** | `svin_stereorig_v1.xml` | `config_stereorig_v1.yaml` | `bus_outside.db3` | AFRL双目+IMU, 压缩图 |
| **Cave** | `svin_stereorig_v2.xml` | `config_stereorig_v2.yaml` | `cave_gennie.db3` | AFRL双目+IMU, 压缩图 |
| **Cemetery** | `svin_stereorig_v1.xml` | `config_stereorig_v1.yaml` | `cemetery.db3` | 同Bus配置 |
| ZED2i 实时 | `svin_zy_zed2i.launch.py` | `config_zy.yaml` | — | ZED2i双目+外置IMU |
| GoPro 水下 | `svin_gopro_uw.xml` | `config_gopro_uw_radtan.yaml` | — | GoPro双目+IMU |
| Aqua2 AUV | `svin_aqua2_A7_uw.launch.py` | `config_aqua2_A7_1280_720.yaml` | — | 水下机器人, 原始图 |
| FLIR 热成像 | `flir_stereo.launch` | `config_flir_stereo_gv7.yaml` | — | 热成像双目 |
| Speedo1 | `svin_speedo1_bbdo2019.launch` | `config_bbdos2019_speedo1.yaml` | — | 水下AUV |
