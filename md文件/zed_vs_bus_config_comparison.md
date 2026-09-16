# ZED 自采数据集 vs Bus 数据集 — 配置文件逐项对比分析

> 数据集: `/home/zhuchao/datebase/202606051639双目和自己imu/202606051639_0.db3`
> 对比基准: Bus 数据集 (`config_stereorig_v1.yaml` + `svin_stereorig_v1.xml`)
> 运行日期: 2026-06-05

---

## 运行结果

| 项目 | ZED (自采) | Bus (基准) |
|------|-----------|-----------|
| VIO 初始化 | ✅ 成功 | ✅ 成功 |
| 关键帧数 | 374 | 1247 |
| 轨迹漂移 | ❌ ~476m / 166s | ✅ < 几米 / 585s |
| PLY 输出 | ❌ 无 | ✅ 正常 |
| Frame delayed | 大量 | 少量 |
| Dropping frame | 大量 | 偶发 |

---

## P0 — IMU 噪声参数（轨迹发散主因）

ZED 内置 IMU (BMI0xx 消费级) vs Bus 外置 IMU (3DM-GV7 工业级)：

| 参数 | 含义 | Bus 值 | ZED 值 | ZED/Bus 比值 |
|------|------|--------|--------|-------------|
| `sigma_g_c` | 陀螺噪声密度 | **0.0016017** | 0.0001763 | **小 9.1 倍** 🔴 |
| `sigma_a_c` | 加速度计噪声密度 | **0.0071376** | 0.0012943 | **小 5.5 倍** 🔴 |
| `sigma_bg` | 陀螺 bias 先验 | 0.03 | 0.03 | 相同 |
| `sigma_ba` | 加速度计 bias 先验 | 0.1 | 0.1 | 相同 |
| `sigma_gw_c` | 陀螺随机游走 | 0.0000165 | 0.00004845 | 大 2.9 倍 |
| `sigma_aw_c` | 加速度计随机游走 | 0.0002874 | 0.0001502 | 小 1.9 倍 |

### 为什么这是主因

```
sigma_g_c 和 sigma_a_c 是 OKVIS Ceres 优化中 IMU 残差的权重：

  值越小 → IMU 残差权重越大 → 系统更"信任"IMU → 跟陀螺走
  值越大 → IMU 残差权重越小 → 系统更"信任"视觉 → 跟图像走

Bus 策略 (sigma_g_c=0.0016): "我不太信陀螺，让视觉约束主导"     → 稳健
ZED 策略 (sigma_g_c=0.00018): "我非常信陀螺，IMU积分说了算"    → 发散
```

kalibr 给出的 IMU 噪声是**曲线拟合的最优值**，反映的是"标定序列中 IMU 的最好表现"。
实际 VIO 需要的是**保守先验**——工业级 IMU (3DM-GV7) 尚且用保守值，消费级 ZED 内置 IMU 却用更激进的值，必然发散。

### 修复

```yaml
imu_params:
    sigma_g_c: 0.0016      # 放大 9 倍
    sigma_a_c: 0.007       # 放大 5-10 倍
    sigma_gw_c: 0.000016   # 参考 Bus 值
    sigma_aw_c: 0.00028    # 参考 Bus 值
```

---

## P1 — 实际运行分辨率（视觉约束不足）

| 参数 | Bus | ZED |
|------|-----|-----|
| 原始分辨率 | 1600 × 1200 | 960 × 540 |
| `resizeFactor` | 0.5 | 0.5 |
| 实际运行分辨率 | **800 × 600** | **480 × 270** |
| 像素量 | 480,000 | 129,600 |
| 像素比 | **3.7 倍** | — |

480×270 下 BRISK 特征点数量严重不足。VIO 需要的视觉约束（重投影误差项）太少，无法有效抑制 IMU 积分漂移。

### 修复

```yaml
resizeFactor: 1.0    # 保持原始 960×540
# 或至少:
# resizeFactor: 0.75  # → 720×405
```

---

## P2 — 图像增强与特征检测

| 参数 | Bus | ZED |
|------|-----|-----|
| `histogramMethod` | **`"CLAHE"`** | `"NONE"` |
| `claheClipLimit` | 1.0 | (缺失) |
| `claheTilesGridSize` | 2 | (缺失) |
| `detection_options.threshold` | **20.0** | 30.0 |
| `detection_options.octaves` | 1 | 1 |
| `maxNoKeypoints` | 400 | 400 |

CLAHE (自适应直方图均衡) 在暗区、亮区、阴影中能显著提升有效特征点数。
关闭 CLAHE + 检测阈值更高(30 vs 20) = 特征点更少 = 视觉约束更弱。

### 修复

```yaml
histogramMethod: "CLAHE"
claheClipLimit: 1.0
claheTilesGridSize: 2

detection_options:
    threshold: 20.0
```

---

## P3 — 帧率配置不匹配

| 参数 | Bus | ZED |
|------|-----|-----|
| `camera_params.camera_rate` | **13** | **20** |
| bag 实际帧率 | ~12.5 Hz | ~13.9 Hz |
| 偏差 | 4% | **43%** |

`stereo_sync.cpp` 用 `camera_rate` 计算双目同步时间窗口：`max_time_diff = 0.5 / camera_rate`。

- `camera_rate=13` → 窗口 38ms → 足够容纳正常帧间隔
- `camera_rate=20` → 窗口 25ms → 偏小，容易判定为不同步而丢帧

43% 的偏差导致大量误判丢帧 (`Dropping frame`)，进一步减少了 VIO 能用的图像。

### 修复

```yaml
camera_params:
    camera_rate: 15    # 接近实际 ~14fps
```

---

## P4 — 回环检测参数（次要）

| 参数 | Bus | ZED |
|------|-----|-----|
| `min_correspondences` | **25** | 20 |
| `pnp_reprojection_threshold` | **20.0** | 25.0 |

Bus 的回环条件更严格。对 166 秒短序列影响不大，但也值得对齐。

---

## Launch 文件对比

| 项目 | Bus (`svin_stereorig_v1.xml`) | ZED (`svin_zed_stereo.launch.py`) |
|------|------|------|
| 格式 | ROS2 XML | ROS2 Python (功能等价) |
| 图像话题 | `/slave1/image_raw` (compressed) | `/zed/zed_node/left/color/raw/image` (raw) |
| `compressed` 参数 | true | false |
| IMU 话题 | `/imu/imu` | `/zed/zed_node/imu/data` |
| okvis_node remap | `/camera0→/cam0/image_raw` | 相同 |
| IMU remap | `/imu→/imu/imu` | `/imu→/zel/zed_node/imu/data` |

Launch 无问题，仅话题名不同。

---

## 数据集本身差异

| 项目 | Bus | ZED |
|------|-----|------|
| 时长 | 585 秒 | 166 秒 |
| 环境 | 室外，丰富纹理 | 未知 |
| IMU 硬件 | 3DM-GV7 (工业级, ~$3000) | ZED 内置 BMI0xx (消费级, ~$2) |
| 噪声水平 | 低 | 高 |
| 相机同步 | 硬件同步 | ZED 内部同步 |

> ZED 内置 IMU 的噪声比 3DM-GV7 高 1-2 个数量级，但 kalibr 标定给出的噪声参数却比 Bus 配置还小——这是根本矛盾。

---

## 修复总结

```yaml
# config_zed_stereo.yaml 需要改的关键值：

# P0: IMU 噪声 — 放大 5-10 倍
sigma_g_c: 0.0016          # 原 0.000176
sigma_a_c: 0.007            # 原 0.00129
sigma_gw_c: 0.000016        # 原 0.000048
sigma_aw_c: 0.00028         # 原 0.00015

# P1: 分辨率 — 至少保持原始
resizeFactor: 1.0           # 原 0.5

# P2: 图像增强
histogramMethod: "CLAHE"    # 原 "NONE"

# P3: 帧率匹配
camera_rate: 15             # 原 20
```

| 优先级 | 问题 | 影响 | 修复难度 |
|--------|------|------|---------|
| P0 | IMU 噪声过于乐观 | 🔴 VIO 发散主因 | 改 4 个数字 |
| P1 | 分辨率太低 (480×270) | 🔴 视觉约束弱 | 改 1 个数字 |
| P2 | 无 CLAHE + 阈值高 | 🟡 特征点少 | 改 3 个参数 |
| P3 | camera_rate 不匹配 | 🟡 时序异常丢帧 | 改 1 个数字 |
