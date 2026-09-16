# SVO 转 Rosbag 录制指南

## 前置准备（只需做一次）

每次重装 ZED SDK 或 rebuild `zed_wrapper` 后需要重新修改配置：

```bash
# 1. 启用左右目图像发布
sed -i "s/publish_left_right: false/publish_left_right: true/" \
  /home/zhuchao/ros2_ws/install/zed_wrapper/share/zed_wrapper/config/common_stereo.yaml

# 2. 启用 IMU raw 数据发布
sed -i "s/publish_imu_raw: false/publish_imu_raw: true/" \
  /home/zhuchao/ros2_ws/install/zed_wrapper/share/zed_wrapper/config/common_stereo.yaml

# 3. 关闭 AI 深度模式（没装 TensorRT 必须改）
sed -i "s/depth_mode: 'NEURAL_LIGHT'/depth_mode: 'PERFORMANCE'/" \
  /home/zhuchao/ros2_ws/install/zed_wrapper/share/zed_wrapper/config/common_stereo.yaml

# 4. 关闭位置追踪（缺少 AI 模型文件会崩溃）
sed -i "s/pos_tracking_enabled: true/pos_tracking_enabled: false/" \
  /home/zhuchao/ros2_ws/install/zed_wrapper/share/zed_wrapper/config/common_stereo.yaml
```

验证修改：
```bash
grep -n "depth_mode\|publish_left_right\|publish_imu_raw\|pos_tracking_enabled" \
  /home/zhuchao/ros2_ws/install/zed_wrapper/share/zed_wrapper/config/common_stereo.yaml
```

期望输出：
```
54:            publish_left_right: true
66:            publish_imu_raw: true
88:            depth_mode: 'PERFORMANCE'
109:            pos_tracking_enabled: false
```

---

## 录制方式

### 方式一：一键脚本（推荐）

```bash
# 1. 编辑脚本，修改 SVO 路径和输出路径
vim /home/zhuchao/svin_ws/record_svo_to_bag.sh

# 2. 运行
bash /home/zhuchao/svin_ws/record_svo_to_bag.sh
```

**脚本位置：** `/home/zhuchao/svin_ws/record_svo_to_bag.sh`

脚本内容：
```bash
#!/bin/bash
# set -e   # 不用 set -e，timeout 退出码 124 会导致脚本中止

source /opt/ros/humble/setup.bash
source /home/zhuchao/ros2_ws/install/setup.bash

SVO_DIR="/media/zhuchao/My Book/小车数据集/20260624/20260624svo"
BAG_DIR="/media/zhuchao/My Book/小车数据集"
TOPICS="/zed/zed_node/left/color/rect/image /zed/zed_node/right/color/rect/image /zed/zed_node/imu/data_raw /zed/zed_node/imu/data"

SVO1="$SVO_DIR/HD1080_SN39099060_17-02-31.svo2"
SVO2="$SVO_DIR/HD1080_SN39099060_17-08-26.svo2"

record_one() {
    local SVO=$1
    local BAG=$2
    local TIMEOUT=$3

    echo "===== 开始录制: $(basename "$SVO") (超时: ${TIMEOUT}s) ====="
    rm -rf "$BAG"

    # Start rosbag recording
    ros2 bag record -o "$BAG" $TOPICS &
    local RECORD_PID=$!
    sleep 2

    # Start SVO playback
    timeout ${TIMEOUT}s ros2 launch zed_wrapper zed_camera.launch.py \
        camera_model:=zed2i \
        svo_path:="$SVO" &
    local ZED_PID=$!

    # Wait for ZED to finish (timeout or SVO end)
    wait $ZED_PID 2>/dev/null || true
    local EXIT_CODE=$?

    sleep 2
    # Stop recording
    kill $RECORD_PID 2>/dev/null
    wait $RECORD_PID 2>/dev/null

    echo "===== 录制完成: $BAG ====="
}

# Record first SVO
record_one "$SVO1" "$BAG_DIR/rosbag2_20260624_svo1" 180
sleep 3
# Record second SVO
record_one "$SVO2" "$BAG_DIR/rosbag2_20260624_svo2" 300

echo "===== 全部完成 ====="
ls -lh "$BAG_DIR"/rosbag2_20260624_svo*/*.db3 2>/dev/null
```

### 方式二：手动两终端

```bash
source /opt/ros/humble/setup.bash
source /home/zhuchao/ros2_ws/install/setup.bash
```

**终端1 — 播放 SVO：**
```bash
ros2 launch zed_wrapper zed_camera.launch.py \
  camera_model:=zed2i \
  svo_path:=/path/to/your.svo2
```

**终端2 — 录制 bag：**
```bash
ros2 bag record -o /path/to/output_bag \
  /zed/zed_node/left/color/rect/image \
  /zed/zed_node/right/color/rect/image \
  /zed/zed_node/imu/data_raw \
  /zed/zed_node/imu/data
```

播完后 `Ctrl+C` 停止录制。

---

## 话题说明

| 话题 | 内容 |
|------|------|
| `/zed/zed_node/left/color/rect/image` | 左目矫正彩色图像 |
| `/zed/zed_node/right/color/rect/image` | 右目矫正彩色图像 |
| `/zed/zed_node/imu/data` | IMU 矫正数据 |
| `/zed/zed_node/imu/data_raw` | IMU 原始数据 |

---

## 注意事项

1. **磁盘空间**：未压缩图片录 bag 非常大（150M SVO → ~21G bag），确保有足够空间
2. **超时时间**：SV2 文件大小 × 1.2 秒/MB ≈ 需要的超时秒数（例如 150MB → 180s，230MB → 300s）
3. **每次 rebuild 后**需要重新执行"前置准备"的 sed 命令
4. **缺少 TensorRT**：必须把 `depth_mode` 改为 `PERFORMANCE` 或 `NONE`
5. **播放 bag**：`ros2 bag play <bag目录>`

---

## 检查话题是否正常

```bash
source /opt/ros/humble/setup.bash
ros2 topic list | grep zed
ros2 topic hz /zed/zed_node/left/color/rect/image  # 查看帧率
```
