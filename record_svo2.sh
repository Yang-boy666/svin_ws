#!/bin/bash

source /opt/ros/humble/setup.bash
source /home/zhuchao/ros2_ws/install/setup.bash

BAG="/media/zhuchao/My Book/小车数据集/rosbag2_20260624_svo2"
SVO="/media/zhuchao/My Book/小车数据集/20260624/20260624svo/HD1080_SN39099060_17-08-26.svo2"
TOPICS="/zed/zed_node/left/color/rect/image /zed/zed_node/right/color/rect/image /zed/zed_node/imu/data_raw /zed/zed_node/imu/data"

rm -rf "$BAG"

echo "===== 开始录制: $(basename "$SVO") ====="

ros2 bag record -o "$BAG" $TOPICS &
RECORD_PID=$!
sleep 3

timeout 300s ros2 launch zed_wrapper zed_camera.launch.py \
    camera_model:=zed2i \
    svo_path:="$SVO" &
ZED_PID=$!

wait $ZED_PID 2>/dev/null || true
sleep 2

kill $RECORD_PID 2>/dev/null
wait $RECORD_PID 2>/dev/null

echo "===== 完成 ====="
ls -lh "$BAG"/*.db3 2>/dev/null
