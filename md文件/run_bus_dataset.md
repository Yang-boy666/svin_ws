# SVIn 完整编译与 Bus 数据集运行指南

## 环境信息

| 项目 | 版本 |
|------|------|
| 操作系统 | Ubuntu 22.04 |
| ROS 2 | Humble |
| OpenCV | 4.5.4 |
| Ceres Solver | 2.0.0 |
| GCC | 11.4.0 |
| CMake | ≥ 3.8 |

---

## 一、安装依赖

### 1.1 系统依赖

```bash
# PCL 点云库
sudo apt install libpcl-dev

# Glog, Gflags, BLAS, LAPACK, Eigen3
sudo apt install libgoogle-glog-dev libgflags-dev \
  libblas-dev liblapack-dev libatlas-base-dev libeigen3-dev

# SuiteSparse 和 OpenCV
sudo apt install libsuitesparse-dev libopencv-dev

# METIS (编译时需要)
# 如果无法安装 libmetis-dev，请参见 1.4 节
sudo apt install libmetis-dev

# ROS 2 Humble 额外包
sudo apt install ros-humble-pcl-ros ros-humble-tf2-sensor-msgs \
  ros-humble-compressed-image-transport
```

### 1.2 BRISK 特征库

```bash
wget https://www.doc.ic.ac.uk/~sleutene/software/brisk-2.0.8.zip
unzip brisk-2.0.8.zip
cd brisk && mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
make -j$(nproc)
sudo make install
```

### 1.3 数据转换工具 (ROS1 bag → ROS2 bag)

```bash
sudo apt install pipx
pipx install rosbags

# 用法：
# rosbags-convert --src <ros1_bag> --dst <ros2_bag_folder>
```

### 1.4 METIS 库问题处理

如果 `libmetis-dev` 安装后 CMake 仍然找不到 METIS，或者只能安装
`libmetis5` 运行时库（无 `.so` 符号链接），需要在编译时手动指定路径：

系统中 METIS 库的实际位置：
```
/usr/lib/x86_64-linux-gnu/libmetis.so.5        ← 运行时库
/usr/lib/x86_64-linux-gnu/libmetis.so.5.1.0    ← 实际文件
```

编译时添加 CMake 参数：
```
-DMETIS_LIBRARY=/usr/lib/x86_64-linux-gnu/libmetis.so.5
```

---

## 二、编译 SVIn

### 2.1 获取源码

```bash
mkdir -p ~/svin_ws/src
cd ~/svin_ws/src
git clone https://github.com/AutonomousFieldRoboticsLab/SVIn.git
```

### 2.2 完整编译命令

```bash
cd ~/svin_ws
source /opt/ros/humble/setup.bash

# 首次编译（含 METIS 路径参数）
colcon build --event-handlers console_direct+ \
  --cmake-args -DMETIS_LIBRARY=/usr/lib/x86_64-linux-gnu/libmetis.so.5

# 后续增量编译（只编译有改动的包）
colcon build --event-handlers console_direct+ \
  --cmake-args -DMETIS_LIBRARY=/usr/lib/x86_64-linux-gnu/libmetis.so.5

# 完全清理重新编译
rm -rf build/ install/ log/
colcon build --event-handlers console_direct+ \
  --cmake-args -DMETIS_LIBRARY=/usr/lib/x86_64-linux-gnu/libmetis.so.5
```

编译成功输出示例：
```
Starting >>> okvis_ros
Finished <<< okvis_ros [3min 54s]
Starting >>> pose_graph
Finished <<< pose_graph [45.9s]
Summary: 2 packages finished [4min 40s]
```

---

## 三、准备数据集

### 3.1 数据集来源

AFRL 水下双目-惯性数据集：
- HuggingFace: https://huggingface.co/datasets/afrl-uw/stereo-vi-underwater-dataset
- Google Drive (Bus/Cave 文件夹): https://drive.google.com/drive/folders/...

### 3.2 放置数据集

将 `.db3` 文件放到 `date_record/` 目录：

```
~/svin_ws/
└── date_record/
    ├── bus_outside.db3      # Bus 数据集 (2.5 GB, 585秒)
    ├── cave_gennie.db3      # Cave 数据集 (7.9 GB, 710秒)
    └── cemetery.db3         # Cemetery 数据集 (2.3 GB)
```

### 3.3 Bus 数据集话题内容

```
/slave1/image_raw/compressed   CompressedImage    7338 帧
/slave2/image_raw/compressed   CompressedImage    7337 帧
/slave1/image_raw/cam_info     CameraInfo         7338 帧
/slave2/image_raw/cam_info     CameraInfo         7337 帧
/imu/imu                       Imu               58487 帧 (100Hz)
/imagenex831l/range            ProcessedRange    55923 帧 (声纳)
/bar30/pressure                FluidPressure       584 帧 (深度)
```

---

## 四、运行 Bus 数据集

### 4.1 一键运行流程

需要 **两个终端**：

**终端 1 — 启动 SVIn 系统：**
```bash
cd ~/svin_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch okvis_ros svin_stereorig_v1.xml
```

系统启动后依次初始化 4 个节点：
| 节点 | 功能 |
|------|------|
| `stereo_sync` | 解压缩并同步双目图像，发布 `/cam0/image_raw`、`/cam1/image_raw` |
| `pose_graph_node` | 回环检测 + 位姿图优化（加载 DBoW2 词袋） |
| `okvis_node` | 视觉惯性里程计 VIO（BRISK 特征 + Ceres 优化） |
| `rviz2` | 可视化（轨迹、点云、特征匹配） |

**终端 2 — 播放数据包：**
```bash
source /opt/ros/humble/setup.bash
ros2 bag play ~/svin_ws/date_record/bus_outside.db3 --clock
```

> `--clock` 参数将 ROS 时钟同步到 bag 时间戳，配合 launch 文件的
> `use_sim_time:=true` 使用。播放时长约 10 分钟。

### 4.2 运行状态检查

正常运行时终端会显示：

```
[okvis_node] Initialized!! As enough keypoints are found   ← VIO 初始化成功
[okvis_node] Received image - encoding: bgr8, width: 800, height: 600   ← 正在处理图像
[pose_graph_node] keyframe_queue Size [#] 1149   ← 关键帧数量持续增长
```

常见警告（无需处理）：
- `Frame delayed at time xxx` — 帧处理延迟（正常）
- `Received image from the past. Dropping the image` — 丢帧（系统略慢于实时播放）
- `Dropping frame with id xxx` — 双目同步丢帧

### 4.3 停止与保存结果

数据包播放完毕后：
1. 等待 ~30 秒让系统处理完残余数据
2. 在**终端 1** 按 `Ctrl+C` 停止
3. 轨迹自动保存，终端显示：
```
[pose_graph_node] Trajectory saved to: .../svin_results/svin_2026_XX_XX_XX_XX_XX.txt
[pose_graph_node] Trajectory PLY saved to: .../svin_results/svin_2026_XX_XX_XX_XX_XX.ply
```

### 4.4 关闭时崩溃说明

`pose_graph_node` 在关闭流程中可能出现：
```
terminate called without an active exception
```
这**不影响轨迹保存**——轨迹在关闭前已经写入磁盘完毕。

---

## 五、运行其他数据集

```bash
# Cave 数据集（终端 1）
ros2 launch okvis_ros svin_stereorig_v2.xml

# Cemetery 数据集（终端 1 — 同 Bus 配置）
ros2 launch okvis_ros svin_stereorig_v1.xml

# 终端 2 — 替换对应的 bag 文件
ros2 bag play ~/svin_ws/date_record/cave_gennie.db3 --clock
ros2 bag play ~/svin_ws/date_record/cemetery.db3 --clock
```

Config 与 Launch 对应关系：
| 场景 | Launch | Config | Bag |
|------|--------|--------|-----|
| **Bus** | `svin_stereorig_v1.xml` | `config_stereorig_v1.yaml` | `bus_outside.db3` |
| **Cave** | `svin_stereorig_v2.xml` | `config_stereorig_v2.yaml` | `cave_gennie.db3` |
| **Cemetery** | `svin_stereorig_v1.xml` | `config_stereorig_v1.yaml` | `cemetery.db3` |
| GoPro 水下 | `svin_gopro_uw.xml` | `config_gopro_uw_radtan.yaml` | — |
| ZED2i 实时 | `svin_zy_zed2i.launch.py` | `config_zy.yaml` | — |

---

## 六、输出文件

### 6.1 轨迹文件

`pose_graph/svin_results/svin_YYYY_MM_DD_HH_MM_SS.txt`

```
#timestamp tx ty tz qx qy qz qw
1494876479.880990200 -0.002973 0.147828 0.202886 -0.617279 0.067690 0.105187 0.776737
1494876479.960420200 -0.002333 0.143707 0.204549 -0.613324 0.067930 0.106272 0.779696
...
```

每行一个关键帧位姿：时间戳 + 平移(tx,ty,tz) + 四元数(qx,qy,qz,qw)。

### 6.2 点云文件

`pose_graph/svin_results/svin_YYYY_MM_DD_HH_MM_SS.ply`

PLY 格式，每个顶点为相机位置。可用 Meshlab、CloudCompare 打开。

### 6.3 调试输出

`pose_graph/debug_output/` 目录：

| 文件/目录 | 内容 |
|-----------|------|
| `loop_closure.txt` | 回环检测结果列表 |
| `loop_closure/` | 回环匹配可视化图像 |
| `pnp_verified/` | PnP 验证可视化图像 |
| `descriptor_matched/` | 描述子匹配可视化图像 |
| `switch_info.txt` | 开关变量状态 |

### 6.4 Bus 数据集运行结果示例

运行完整的 585 秒 Bus 数据集，输出：

| 指标 | 数值 |
|------|------|
| 关键帧数 | 1247 |
| 轨迹文件大小 | 134 KB |
| 点云文件大小 | 46 KB |
| 覆盖时间范围 | 584.7 秒（完整） |

---

## 七、验证地面真值

COLMAP 伪地面真值位于 `src/SVIn/colmap_groundtruth/bus_outside.txt`：

```bash
# 查看真值
head -5 src/SVIn/colmap_groundtruth/bus_outside.txt
# 输出格式: #timestamp px py pz qx qy qz qw
```

> **注意**：COLMAP 真值仅精确到未知尺度，评估需要在缩放对齐后进行。
> 未来将发布使用双目外参约束的尺度精确轨迹。

---

## 八、故障排除

### 8.1 编译错误

| 错误 | 原因 | 解决 |
|------|------|------|
| `METIS_LIBRARY set to NOTFOUND` | METIS 开发库缺失或路径不对 | 添加 `-DMETIS_LIBRARY=/usr/lib/x86_64-linux-gnu/libmetis.so.5` |
| `find_package(Ceres 2.1 REQUIRED)` 失败 | 系统 Ceres 版本为 2.0.0 (< 2.1) | CMake 版本检查存在兼容性问题，通常能通过。如失败，可安装新版 Ceres 或将 `USE_SYSTEM_CERES` 设为 `OFF` |

### 8.2 运行时崩溃

| 现象 | 原因 | 解决 |
|------|------|------|
| `double free or corruption` (exit code -6) | 内存不足或多进程冲突 | `pkill -9 -f "okvis\|pose_graph\|stereo_sync"` 清理残留进程 |
| `exit code -9` (SIGKILL) | OOM Killer 杀死进程 | 关闭 RViz、清理残留进程、确保 ≥8GB 可用内存 |
| okvis_node 初始化时崩溃 | 初始化后立即内存异常 | 确认系统内存足够，残留进程已清理 |

### 8.3 运行中问题

| 现象 | 原因 | 解决 |
|------|------|------|
| 大量 "Frame delayed" | 处理速度跟不上播放速度 | 正常现象，不影响轨迹质量 |
| 轨迹文件很小（几行） | 系统启动后 okvis 崩溃 | 查看终端输出确认崩溃原因，按 8.2 排查 |
| RViz 不显示 | OpenGL/显卡驱动问题 | 可忽略，不影响轨迹生成 |

### 8.4 内存不足

```bash
# 检查内存
free -h

# 清理所有残留进程
pkill -9 -f "okvis_node|stereo_sync|pose_graph_node|rviz2|ros2 bag|ros2 launch"

# 不启动 RViz 以节省内存
# 编辑 launch 文件，删除 rviz2 节点块
```

---

## 九、常用命令速查

```bash
# === 环境 ===
source /opt/ros/humble/setup.bash              # ROS 2 环境
source ~/svin_ws/install/setup.bash            # SVIn 环境

# === 编译 ===
colcon build --event-handlers console_direct+ \
  --cmake-args -DMETIS_LIBRARY=/usr/lib/x86_64-linux-gnu/libmetis.so.5

# === 运行 ===
ros2 launch okvis_ros svin_stereorig_v1.xml    # 启动 SVIn (Bus)
ros2 bag play date_record/bus_outside.db3 --clock  # 播放数据

# === 调试 ===
ros2 bag info date_record/bus_outside.db3      # 查看 bag 信息
ros2 topic list                                # 查看话题列表
ros2 topic echo /okvis/odometry                # 查看里程计输出

# === 清理 ===
pkill -9 -f "okvis|pose_graph|stereo_sync|rviz2|ros2 bag"  # 停止所有进程
rm -rf build/ install/ log/                    # 完全清理编译产物
```

---

## 十、适配自定义传感器

简化为 3 步：

**1. 创建配置文件：**
```bash
cp config/config_stereorig_v1.yaml config/config_my_sensor.yaml
```
编辑 `config_my_sensor.yaml`：
- `cameras[].focal_length` / `principal_point` → 你的相机内参
- `cameras[].T_SC` → 你的相机外参
- `imu_params.T_BS` → 你的 IMU 外参
- `imu_params.sigma_*` → 你的 IMU 噪声参数
- `camera_params.camera_rate` → 你的相机帧率

**2. 创建 Launch 文件：**
```bash
cp okvis_ros/launch/svin_stereorig_v1.xml okvis_ros/launch/svin_my_sensor.xml
```
编辑话题名和 config 路径。

**3. 编译运行：**
```bash
colcon build --cmake-args -DMETIS_LIBRARY=/usr/lib/x86_64-linux-gnu/libmetis.so.5
ros2 launch okvis_ros svin_my_sensor.xml
```
