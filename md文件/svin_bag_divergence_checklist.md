# SVIn 数据包发散排查清单

本文用于记录为什么 AFRL bus 数据包能稳定运行，而自采 ZED + mFOSN IMU 数据包容易发散，并作为后续新数据包的固定检查流程。

后续如果重新采集数据包，可以把这个文件和新数据包路径一起发给 Codex，然后按本文流程逐项检验。

## 一、当前已知结论

bus 数据包稳定，主要原因不是图像质量更好，而是数据与配置更自洽：

- 相机帧率配置与实际帧率接近。
- 相机和 IMU 时间戳连续性较好。
- 双目、IMU、外参、时间偏移属于同一套官方数据。
- `T_BS`、`T_SC`、`imageDelay` 等参数与数据采集系统匹配。

自采 20260528 数据包发散，主要疑点如下：

- 相机和 IMU 都出现约 1.2 秒级断流。
- 配置 `camera_rate: 30`，但 bag 实测相机只有约 13.6Hz。
- Kalibr 结果提示 `timeshift_cam_imu ≈ -0.09s`，但配置里 `imageDelay: 0.0`。
- `T_SC` 外参方向需要重新确认，不能只靠注释判断。
- `T_BS` 当前为单位阵，需要确认 mFOSN IMU 坐标系是否真的等同于 body 坐标系。
- 图像质量不是主要问题，自采数据 ORB 特征数量和清晰度都足够。

## 二、对比基准

### 1. bus 数据包

运行说明文件：

```bash
/home/zhuchao/svin_ws/run_bus_dataset.md
```

常用配置：

```bash
/home/zhuchao/svin_ws/src/SVIn/config/config_stereorig_v1.yaml
```

关键特征：

- 图像话题：`/slave1/image_raw/compressed`、`/slave2/image_raw/compressed`
- IMU 话题：`/imu/imu`
- 相机实际频率：约 12.54Hz
- 配置 `camera_rate: 13`
- IMU 实际频率：约 100Hz
- 相机最大间隔：约 0.159s
- IMU 最大间隔：约 0.033s
- 轨迹不出现 NaN，关键帧持续增长。

### 2. 20260528 自采数据包

数据包：

```bash
/home/zhuchao/datebase/20260528/ros2_bag
```

常用配置：

```bash
/home/zhuchao/svin_ws/src/SVIn/config/config_mFOSN_zed.yaml
```

关键特征：

- 图像话题：`/zed/zed_node/left/color/raw/image`、`/zed/zed_node/right/color/raw/image`
- IMU 话题：`/imu`
- 图像编码：`bgra8`
- 相机实际频率：约 13.6Hz
- 配置 `camera_rate: 30`
- IMU 实际频率：约 196Hz
- 相机最大间隔：约 1.2s
- IMU 最大间隔：约 1.19s
- 运行能初始化，但轨迹很快出现 `-nan`。
- 日志中有大量 `Dropping frame` 和 `Frame delayed`。

## 三、新数据包固定检查流程

### 1. 检查 metadata

先确认 bag 路径和话题数量：

```bash
ros2 bag info /path/to/new_bag
```

重点记录：

- 左目图像话题名称
- 右目图像话题名称
- IMU 话题名称
- 图像消息类型
- IMU 消息类型
- 图像帧数
- IMU 帧数
- bag 总时长

期望：

- 左右目帧数应基本一致。
- IMU 数量应明显高于图像数量。
- 总时长、图像数量、IMU 数量算出的频率应合理。

### 2. 检查实际频率和断流

用 Python 读取 sqlite 数据库统计 timestamp 间隔。示例：

```bash
python3 - <<'PY'
import sqlite3, statistics

db = "/path/to/new_bag/xxx.db3"

con = sqlite3.connect(db)
cur = con.cursor()
topics = {row[0]: (row[1], row[2]) for row in cur.execute("select id,name,type from topics order by id")}

for tid, (name, typ) in topics.items():
    ts = [r[0] for r in cur.execute("select timestamp from messages where topic_id=? order by timestamp", (tid,))]
    if len(ts) < 2:
        continue
    dur = (ts[-1] - ts[0]) / 1e9
    hz = (len(ts) - 1) / dur if dur > 0 else 0
    dts = [(b - a) / 1e9 for a, b in zip(ts, ts[1:])]
    threshold = 2.5 / hz if hz > 0 else 1.0
    gaps = [dt for dt in dts if dt > threshold]
    print(f"{tid}: {name}")
    print(f"  type={typ}")
    print(f"  n={len(ts)} dur={dur:.3f}s hz={hz:.3f}")
    print(f"  dt_med={statistics.median(dts):.4f}s dt_min={min(dts):.4f}s dt_max={max(dts):.4f}s")
    print(f"  gaps>{threshold:.3f}s: {len(gaps)} max_gap={max(gaps) if gaps else 0:.4f}s")
PY
```

判断标准：

- 相机最大间隔最好不要超过正常帧间隔的 2 到 3 倍。
- IMU 最大间隔最好不要出现 0.1s 以上的大断流。
- 如果相机或 IMU 出现 1 秒级断流，VIO 很容易发散。

### 3. 检查 header 时间戳

需要确认 message header 时间和 rosbag record 时间是否一致，至少不要乱跳。

重点看：

- `record_time - header_time` 是否基本稳定。
- 左右目 header 是否能近邻匹配。
- IMU header 是否单调递增。

判断标准：

- record 和 header 的绝对差值可以不是 0，但必须稳定。
- 左右目最近邻时间差最好在 5ms 内，偶尔 10ms 以内通常还能接受。
- 如果大量左右目差值超过 20ms，要优先检查 ZED 录制设置和同步方式。

### 4. 检查图像编码和质量

自采 ZED 数据常见编码：

- `bgra8`
- `bgr8`
- `rgb8`
- `mono8`

SVIn 当前已经兼容 `bgra8` 和 `rgba8`，会转成灰度图进入前端。

需要检查：

- 图像是否过暗。
- 是否严重模糊。
- 是否有大面积纯黑。
- ORB/BRISK 特征是否足够。

经验判断：

- 如果抽样图像 ORB 特征能稳定超过几百个，图像质量通常不是首要问题。
- 如果特征很少，再调整曝光、光照、运动速度和特征阈值。

### 5. 检查配置中的 `camera_rate`

配置文件位置示例：

```bash
/home/zhuchao/svin_ws/src/SVIn/config/config_mFOSN_zed.yaml
```

重点字段：

```yaml
camera_params:
    camera_rate: 30
```

判断标准：

- `camera_rate` 应接近 bag 的实际图像频率。
- 如果实际是 13.6Hz，建议先设为 `14`。
- 如果实际是 15Hz，建议设为 `15`。
- 如果实际是 30Hz，才设为 `30`。

原因：

`stereo_sync.cpp` 中会用 `camera_rate` 计算双目同步容忍参数：

```cpp
max_time_diff_between_msgs = 0.5 / frame_rate
```

配置过高会导致同步容忍度偏小，容易放大丢帧。

### 6. 检查 `imageDelay`

重点字段：

```yaml
imageDelay: 0.0
```

如果 Kalibr 输出里有：

```text
timeshift_cam_imu
```

必须重点测试。

SVIn 代码中图像时间会这样修正：

```cpp
t -= imageDelay
```

建议扫描测试：

```yaml
imageDelay: 0.0
imageDelay: -0.03
imageDelay: -0.06
imageDelay: -0.09
imageDelay: 0.03
imageDelay: 0.06
imageDelay: 0.09
```

判断标准：

- 哪个值能避免 NaN，优先保留。
- 哪个值关键帧持续增长、轨迹尺度合理，优先保留。
- 如果 `±0.09s` 附近明显改善，说明相机和 IMU 时间偏移是主因。

### 7. 检查 `T_SC` 外参方向

重点字段：

```yaml
cameras:
    - {T_SC: [...]}
```

必须确认：

- Kalibr 输出的是 `T_cam_imu` 还是 `T_imu_cam`。
- 当前配置是否做了正确方向转换。
- SVIn/OKVIS 实际使用 `T_SC` 的方向是否与配置一致。

注意：

不要只靠注释判断。代码里对 `T_SC` 的注释存在不完全一致的地方，应该用实际投影或已知静态姿态验证。

建议验证方法：

- 用 Kalibr 原始结果和当前 YAML 做矩阵乘法检查。
- 确认左右相机相对 baseline 是否合理。
- 对 ZED2i，左右目 baseline 通常应接近实际硬件基线。
- 如果取逆前后只有一个方向能得到合理投影，应采用那个方向。

### 8. 检查 `T_BS` 和 IMU 坐标系

重点字段：

```yaml
imu_params:
    T_BS: [...]
```

当前 20260528 配置为单位阵：

```yaml
T_BS:
    [1, 0, 0, 0,
     0, 1, 0, 0,
     0, 0, 1, 0,
     0, 0, 0, 1]
```

必须确认：

- mFOSN IMU 坐标系是否真的等同于 body 坐标系。
- x/y/z 轴方向是否和 SVIn 期望一致。
- 静止时加速度方向是否与重力方向解释一致。
- 角速度正方向是否和相机运动方向一致。

如果 IMU 坐标轴方向错，即使图像很好，也会很快发散。

### 9. 检查 IMU 噪声参数

重点字段：

```yaml
sigma_g_c
sigma_a_c
sigma_bg
sigma_ba
sigma_gw_c
sigma_aw_c
imu_rate
```

判断标准：

- `imu_rate` 应接近实际 IMU 频率。
- 噪声密度应来自 IMU 标定或厂家参数。
- 不要盲目把 IMU 权重调得极低或极高。

建议：

- 先保证时间同步和外参正确，再调噪声。
- 如果外参或时间偏移错，调噪声通常只能掩盖问题，不能真正解决。

### 10. 检查运行日志

运行后重点搜索：

```bash
rg -n "Initialized|Dropping frame|Frame delayed|nan|NaN|PoseGraph watchdog|keyframe_queue" /tmp/ros_logs_svin
```

判断标准：

- 出现 `Initialized!! As enough keypoints are found`：说明前端能初始化。
- `keyframe_queue` 持续增长：说明系统仍在处理。
- 大量 `Dropping frame`：说明同步、处理速度或数据连续性有问题。
- 大量 `Frame delayed`：说明节点处理跟不上或时间队列异常。
- `PoseGraph watchdog`：说明长时间没有新关键帧。
- 轨迹文件出现 `nan` 或 `-nan`：说明估计已经数值发散。

## 四、推荐修复顺序

每次只改一个变量，避免多个因素叠加后无法判断。

1. 修正 `camera_rate` 为实测相机频率。
2. 检查并处理 bag 中的相机/IMU 断流。
3. 扫描测试 `imageDelay`。
4. 重新核对 `T_SC` 外参方向。
5. 重新核对 `T_BS` 和 IMU 坐标轴。
6. 再调 IMU 噪声参数。
7. 最后再调特征阈值、窗口大小、回环和健康恢复参数。

## 五、新数据包给 Codex 时需要提供的信息

请提供：

- 新数据包路径。
- 使用的 launch 文件。
- 使用的 config 文件。
- 左目话题名。
- 右目话题名。
- IMU 话题名。
- 是否使用 ZED 内置 IMU，还是外接 mFOSN IMU。
- Kalibr 输出文件或至少 `T_cam_imu`、`timeshift_cam_imu`。
- 采集时相机目标帧率。
- 采集时 IMU 目标频率。
- 采集过程是否有卡顿、暂停、黑屏或 USB/网络丢包。

如果不确定话题名，只提供 bag 路径即可，Codex 可以从 metadata 自动读取。

## 六、判断结果是否变好的标准

一次运行结果至少要满足：

- `okvis_node` 正常初始化。
- `keyframe_queue` 持续增长。
- `Dropping frame` 数量明显减少。
- 没有 `PoseGraph watchdog`。
- 轨迹文件没有 `nan` 或 `-nan`。
- 轨迹平移尺度在合理范围内，不出现几千米、几百万米级跳变。
- RViz 轨迹连续，不突然飞走。

只有满足这些条件，才算从“能跑”进入“可信”。
