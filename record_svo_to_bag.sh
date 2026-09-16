#!/bin/bash
# set -e   # 不用 set -e，timeout 退出码 124 会导致脚本中止

source /opt/ros/humble/setup.bash
source /home/zhuchao/ros2_ws/install/setup.bash

SVO_DIR="/media/zhuchao/My Book/小车数据集/20260624/20260624svo"
BAG_DIR="/media/zhuchao/My Book/小车数据集"
TOPICS="/zed/zed_node/left/color/rect/image /zed/zed_node/right/color/rect/image /zed/zed_node/imu/data_raw /zed/zed_node/imu/data"

SVO1="$SVO_DIR/HD1080_SN39099060_17-02-31.svo2"  # 150MB
SVO2="$SVO_DIR/HD1080_SN39099060_17-08-26.svo2"  # 231MB

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

    # Wait for ZED to finish (timeout exits with 124 = SVO ended normally)
    wait $ZED_PID 2>/dev/null || true
    local EXIT_CODE=$?

    sleep 2
    # Stop recording
    kill $RECORD_PID 2>/dev/null
    wait $RECORD_PID 2>/dev/null

    echo "===== 录制完成: $BAG ====="
}

# Record first SVO (~1.5 min)
record_one "$SVO1" "$BAG_DIR/rosbag2_20260624_svo1" 360

sleep 3

# Record second SVO (~4 min)
record_one "$SVO2" "$BAG_DIR/rosbag2_20260624_svo2" 600

echo "===== 全部完成 ====="
ls -lh "$BAG_DIR"/rosbag2_20260624_svo*/*.db3 2>/dev/null
