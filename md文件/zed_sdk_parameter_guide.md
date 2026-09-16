# ZED SDK 参数修改指南

> 文档目的：明确 ZED 相机参数在哪些文件中修改，以及修改后哪些关联文件需要同步更新。
> 适用版本：ZED SDK 4.x + ROS 2 Humble + SVIn

---

## 一、参数涉及的文件总览

```
录制阶段 (ZED SDK)              处理阶段 (SVIn)
─────────────────────          ─────────────────────
zed-ros2-wrapper/config/       svin_ws/src/SVIn/config/
  └─ zed2i.yaml                  └─ config_zed_stereo.yaml
     ├─ 分辨率                       ├─ image_dimension   ← 必须匹配
     ├─ 帧率                         ├─ camera_rate       ← 必须匹配
     ├─ 曝光/增益                    ├─ resizeFactor      ← 影响处理分辨率
     └─ 图像编码                     ├─ focal_length      ← 分辨率变则内参变
        └─ principal_point   ← 分辨率变则内参变
                                svin_ws/src/SVIn/okvis_ros/launch/
                                  └─ svin_zed_stereo.launch.py
                                     └─ 话题名 ← 必须匹配
```

---

## 二、ZED SDK 录制端参数（决定录到什么数据）

### 2.1 配置文件位置

ZED ROS 2 Wrapper 的配置文件通常位于：

```
# 如果用 apt 安装的 zed-ros2-wrapper
/opt/ros/humble/share/zed_wrapper/config/zed2i.yaml

# 如果手动编译安装
~/ros2_ws/src/zed-ros2-wrapper/zed_wrapper/config/zed2i.yaml
```

### 2.2 关键参数

```yaml
# ============================================
# zed2i.yaml 中影响 SVIn 的参数
# ============================================

general:
    camera_model:        'zed2i'       # 相机型号
    grab_resolution:     'HD720'       # ★ 分辨率: HD2K/HD1080/HD720/VGA
    grab_frame_rate:      15           # ★ 帧率: 15/30/60/100

video:
    brightness:           4            # 亮度 (-1 ~ 8)
    contrast:             4            # 对比度 (0 ~ 8)
    saturation:           4            # 饱和度 (0 ~ 8)
    exposure:             80           # 曝光 (1 ~ 100, -1=自动)
    gain:                 80           # 增益 (1 ~ 100, -1=自动)
    whitebalance_temperature: 4600     # 白平衡 (2800~6500, -1=自动)

pos_tracking:                         # 如果用到视觉里程计
    pos_enabled:         false        # SVIn 做 VIO 时建议关闭，节省资源
```

### 2.3 ZED2i 分辨率对照表

| grab_resolution | 宽 × 高 | 像素量 | 建议 resizeFactor |
|-----------------|---------|--------|-------------------|
| `HD2K` | 2208 × 1242 | 2.7M | 0.5 → 1104×621 |
| `HD1080` | 1920 × 1080 | 2.1M | 0.5 → 960×540 |
| **`HD720`** | **1280 × 720** | **0.9M** | **1.0 → 1280×720** ✅ 推荐 |
| `VGA` | 672 × 376 | 0.25M | ❌ 太低 |

> **推荐 HD720 + resizeFactor: 1.0**：1280×720 提供足够特征点，同时不占用过多处理资源。

### 2.4 修改分辨率后必须重新标定

```
分辨率改变 → 相机内参改变 (fx,fy,cx,cy) → 必须重新 kalibr 标定
```

如果你从 `HD720` 改为 `HD1080`，旧的内参和畸变系数不再适用。

---

## 三、SVIn 处理端参数（决定如何处理已录制的数据）

### 3.1 主配置文件

```
~/svin_ws/src/SVIn/config/config_zed_stereo.yaml
```

### 3.2 需要与 ZED 录制参数匹配的字段

```yaml
cameras:
    - image_dimension: [1280, 720]     # ← 必须等于 ZED 录制分辨率
      focal_length: [xxx, xxx]         # ← 必须来自该分辨率下的标定
      principal_point: [xxx, xxx]      # ← 必须来自该分辨率下的标定
      distortion_coefficients: [...]   # ← 必须来自该分辨率下的标定

camera_params:
    camera_rate: 15                    # ← 必须接近 ZED 录制帧率

resizeFactor: 1.0                      # ← 决定实际处理分辨率
```

### 3.3 `resizeFactor` 的作用

```
实际处理分辨率 = image_dimension × resizeFactor

例如:
  image_dimension: [1280, 720], resizeFactor: 1.0  → 处理 1280×720
  image_dimension: [1280, 720], resizeFactor: 0.5  → 处理 640×360
  image_dimension: [1280, 720], resizeFactor: 0.75 → 处理 960×540

内参自动按比例缩放:
  focal_length_effective = focal_length × resizeFactor
  principal_point_effective = principal_point × resizeFactor
```

> 不需要手动缩放内参，SVIn 内部自动处理。只需填原始分辨率的标定值。

### 3.4 Launch 文件

```
~/svin_ws/src/SVIn/okvis_ros/launch/svin_zed_stereo.launch.py
```

需要确保话题名与 ZED 录制/发布的话题一致：

```python
stereo_sync_node = Node(
    parameters=[{
        'left_img_topic':  '/zed/zed_node/left/color/raw/image',   # ← 左目话题
        'right_img_topic': '/zed/zed_node/right/color/raw/image',  # ← 右目话题
        'compressed': False,
    }]
)

okvis_node = Node(
    remappings=[
        ('/imu', '/zed/zed_node/imu/data'),  # ← IMU 话题
    ]
)
```

---

## 四、完整修改流程示例

### 场景：从 960×540@20fps 改为 1280×720@15fps

#### Step 1 — 修改 ZED 录制参数

```yaml
# zed2i.yaml
general:
    grab_resolution:     'HD720'      # 从 HD540(960x540) 改为 HD720(1280x720)
    grab_frame_rate:      15          # 从 20 降为 15（分辨率高了，帧率降低）
```

#### Step 2 — 重新标定（Kalibr）

```bash
# 使用新分辨率的 bag 重新标定
rosrun kalibr kalibr_calibrate_imu_camera \
    --bag new_hd720_calibration.bag \
    --target aprilgrid.yaml \
    --cam new_camchain.yaml \
    --imu imu.yaml
```

#### Step 3 — 更新 SVIn 配置

```yaml
# config_zed_stereo.yaml
cameras:
    - image_dimension: [1280, 720]                         # ← 改为新分辨率
      focal_length: [xxx, xxx]                             # ← 填新标定值
      principal_point: [xxx, xxx]                          # ← 填新标定值
      distortion_coefficients: [...]                       # ← 填新标定值
      T_SC: [...]                                          # ← 如果重新标定，用新的 T_ic

camera_params:
    camera_rate: 15                                        # ← 匹配新帧率

resizeFactor: 1.0                                          # 1280×720 足够用，不缩放
```

#### Step 4 — 编译运行

```bash
cd ~/svin_ws
colcon build --cmake-args -DMETIS_LIBRARY=/usr/lib/x86_64-linux-gnu/libmetis.so.5
ros2 launch okvis_ros svin_zed_stereo.launch.py
```

---

## 五、改动影响关系图

```
                    ZED SDK 参数改了哪个？
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
       分辨率变了      帧率变了      曝光/增益变了
          │              │              │
          ├─ 需要重新标定  ├─ camera_rate  │─ 不影响标定
          ├─ image_dimension │  必须匹配    │─ 可能影响 CLAHE 效果
          ├─ focal_length   │              │
          ├─ principal_point│              │
          ├─ distortion     │              │
          └─ T_SC 可能更新  │              │
                            │              │
                     SVIn config 哪些字段要改？
                     ┌──────────────────────┐
                     │ image_dimension  ←── 分辨率
                     │ focal_length     ←── 标定
                     │ principal_point  ←── 标定
                     │ distortion_coeffs ←─ 标定
                     │ T_SC             ←── 标定(如重新标定)
                     │ camera_rate      ←── 帧率
                     │ resizeFactor     ←── 综合决定
                     └──────────────────────┘
```

---

## 六、快速检查清单

运行前逐项确认：

```
□ ZED 录制分辨率 = SVIn image_dimension ?
□ ZED 录制帧率   ≈ SVIn camera_rate (误差 < 20%) ?
□ SVIn 内参来自「同分辨率」下的标定 ?
□ T_SC 方向正确 (Camera→IMU, 即 Kalibr 的 T_ic) ?
□ Launch 文件中话题名 = bag 中实际话题名 ?
□ resizeFactor 合理 (处理后 ≥ 640×480 为宜) ?
```

---

## 七、常见错误

| 错误现象 | 根因 | 修复 |
|---------|------|------|
| 大量 `Frame delayed` | `camera_rate` 与实际帧率偏差大 | 对齐 `camera_rate` |
| VIO 初始化后立即发散 | `image_dimension` 与 bag 不匹配 | 检查 bag 实际分辨率 |
| 特征点极少 | 分辨率太低或 CLAHE 未开 | `resizeFactor: 1.0` + `histogramMethod: CLAHE` |
| 轨迹尺度异常 | `focal_length` 填了其他分辨率的标定值 | 同分辨率重新标定 |
| 左右目视差不合理 | `T_SC` 的方向弄反了(T_ci vs T_ic) | 用 T_ic (Camera→IMU) |
