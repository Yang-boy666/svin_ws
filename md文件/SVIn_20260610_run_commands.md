# SVIn 20260610 Bag Run Commands

Date: 2026-06-10

## Inputs

- Config: `/home/zhuchao/svin_ws/src/SVIn/config/config_zed_stereo_20260610.yaml`
- Bag: `/media/zhuchao/My Book/zy jetson/数据集/20260610/20260610双目标定数据`
- IMU topic in bag: `/zed/zed_node/imu/data_raw`
- Left image topic in bag: `/zed/zed_node/left/color/raw/image`
- Right image topic in bag: `/zed/zed_node/right/color/raw/image`

## Bag Info

```bash
source /opt/ros/humble/setup.bash
ROS_LOG_DIR=/tmp/ros_logs_svin ros2 bag info '/media/zhuchao/My Book/zy jetson/数据集/20260610/20260610双目标定数据'
```

Observed:

- Duration: `88.902384769s`
- Size: `18.5 GiB`
- Messages: `20067`
- Topics:
  - `/zed/zed_node/imu/data_raw`: `17673`
  - `/zed/zed_node/left/color/raw/image`: `1197`
  - `/zed/zed_node/right/color/raw/image`: `1197`

## Run Commands

One-command RViz replay launch:

```bash
source /opt/ros/humble/setup.bash
source /home/zhuchao/svin_ws/install/setup.bash
ROS_LOG_DIR=/tmp/ros_logs_svin ros2 launch okvis_ros svin_zed_20260610_rviz.launch.py
```

This starts `stereo_sync`, `okvis_node`, `pose_graph_node`, `rviz2`, and then plays the 20260610 bag after a 3 second delay. It uses `/zed/zed_node/imu/data_raw` by default.

If you want to start SVIn + RViz but play the bag manually:

```bash
source /opt/ros/humble/setup.bash
source /home/zhuchao/svin_ws/install/setup.bash
ROS_LOG_DIR=/tmp/ros_logs_svin ros2 launch okvis_ros svin_zed_20260610_rviz.launch.py play_bag:=false
```

Terminal 1, stereo image synchronization:

```bash
source /opt/ros/humble/setup.bash
source /home/zhuchao/svin_ws/install/setup.bash
ROS_LOG_DIR=/tmp/ros_logs_svin ros2 run okvis_ros stereo_sync --ros-args \
  -p config_filename:=/home/zhuchao/svin_ws/src/SVIn/config/config_zed_stereo_20260610.yaml \
  -p left_img_topic:=/zed/zed_node/left/color/raw/image \
  -p right_img_topic:=/zed/zed_node/right/color/raw/image \
  -p compressed:=false
```

Terminal 2, OKVIS/SVIn VIO:

```bash
source /opt/ros/humble/setup.bash
source /home/zhuchao/svin_ws/install/setup.bash
ROS_LOG_DIR=/tmp/ros_logs_svin ros2 run okvis_ros okvis_node --ros-args \
  -p config_filename:=/home/zhuchao/svin_ws/src/SVIn/config/config_zed_stereo_20260610.yaml \
  -p mesh_file:=firefly.dae \
  -r /camera0:=/cam0/image_raw \
  -r /camera1:=/cam1/image_raw \
  -r /imu:=/zed/zed_node/imu/data_raw
```

Terminal 3, pose graph:

```bash
source /opt/ros/humble/setup.bash
source /home/zhuchao/svin_ws/install/setup.bash
ROS_LOG_DIR=/tmp/ros_logs_svin ros2 run pose_graph pose_graph_node --ros-args \
  -p config_file:=/home/zhuchao/svin_ws/src/SVIn/config/config_zed_stereo_20260610.yaml
```

Terminal 4, play the bag:

```bash
source /opt/ros/humble/setup.bash
ROS_LOG_DIR=/tmp/ros_logs_svin ros2 bag play '/media/zhuchao/My Book/zy jetson/数据集/20260610/20260610双目标定数据'
```

## Results

Generated trajectory files:

```text
/home/zhuchao/svin_ws/src/SVIn/pose_graph/svin_results/svin_2026_06_10_18_47_10.txt
/home/zhuchao/svin_ws/src/SVIn/pose_graph/svin_results/svin_2026_06_10_18_47_10.ply
```

Result sizes:

```text
svin_2026_06_10_18_47_10.txt: 765 lines, 82 KiB
svin_2026_06_10_18_47_10.ply: 771 lines, 29 KiB
```

First trajectory sample:

```text
#timestamp tx ty tz qx qy qz qw
1781062134.936406955 0.002082649 0.023050825 0.000422985 0.011883237 -0.022490082 -0.001892239 0.999674649
```

Last trajectory sample:

```text
1781062223.89398955 1.936584753 -1.485734052 -1.599073949 -0.027853326 -0.022134001 -0.232276899 0.971998827
```

## Notes

- The first sandboxed ROS2 run produced DDS socket errors (`Operation not permitted`), so the ROS2 nodes were run outside the sandbox with approval.
- `okvis_node` successfully read the 20260610 config and resized camera intrinsics by `resizeFactor: 0.5`.
- `okvis_node` received `bgra8`, `1920x1080` images and generated keyframes up to about `Keyframe Index: 763`.
- `pose_graph_node` reported `keyframe_queue Size` around `764`.
- `ros2 bag play` repeatedly warned `Message queue starved. Messages will be delayed`; for a cleaner replay, use a larger `--read-ahead-queue-size` or slower playback rate.
- After stopping with `Ctrl-C`, `pose_graph_node` saved the trajectory files, then aborted during shutdown. The output files above were already written.

## 2026-06-10 Optical-Frame Extrinsic Test

Updated `/home/zhuchao/svin_ws/src/SVIn/config/config_zed_stereo_20260610.yaml`:

- Changed `T_SC` to include the ZED non-optical camera frame to optical frame axis conversion.
- Changed `camera_params.camera_rate` from `30` to `14`, matching the bag's observed image rate more closely.

Command:

```bash
source /opt/ros/humble/setup.bash
source /home/zhuchao/svin_ws/install/setup.bash
ROS_LOG_DIR=/tmp/ros_logs_svin ros2 launch okvis_ros svin_zed_20260610_rviz.launch.py
```

Generated trajectory files:

```text
/home/zhuchao/svin_ws/src/SVIn/pose_graph/svin_results/svin_2026_06_10_19_12_58.txt
/home/zhuchao/svin_ws/src/SVIn/pose_graph/svin_results/svin_2026_06_10_19_12_58.ply
```

Trajectory statistics:

```text
points: 444
duration: 88.220 s
path length: 25.686 m
start/end displacement: 0.071 m
XYZ range: [1.638, 0.701, 0.370] m
median step: 0.0406 m
max step: 0.5573 m
```

Comparison:

```text
previous 19_00_45 run: path 5214.892 m, displacement 3249.080 m, XYZ range [989.700, 3826.442, 995.434] m
previous 18_47_10 run: path 87.805 m, displacement 2.929 m, XYZ range [17.948, 4.869, 7.270] m
bus_outside reference: path 54.721 m, displacement 2.609 m, XYZ range [4.828, 1.903, 11.254] m
```

Observation:

- The optical-frame corrected extrinsics remove the kilometer-scale divergence.
- The resulting trajectory is still too compact/jittery, so further work should focus on timestamp ordering/playback load and confirming the exact ZED optical-frame TF.

## 2026-06-10 Synchronization Code Fix and Slow Replay

Code changes:

- `src/SVIn/okvis_ros/src/stereo_sync.cpp`: publish the synchronized common header on `/cam0/image_raw` and `/cam1/image_raw` in both raw and compressed paths. Previously the synchronized header was computed but the raw messages were republished with their original headers.
- `src/SVIn/okvis_ros/src/okvis_node.cpp`: changed the ROS2 executor from `MultiThreadedExecutor` to `SingleThreadedExecutor` so image/IMU callbacks are serialized under heavy bag replay load.

Build command:

```bash
source /opt/ros/humble/setup.bash
colcon build --packages-select okvis_ros --symlink-install
```

Run command:

```bash
source /opt/ros/humble/setup.bash
source /home/zhuchao/svin_ws/install/setup.bash
ROS_LOG_DIR=/tmp/ros_logs_svin ros2 launch okvis_ros svin_zed_20260610_rviz.launch.py bag_rate:=0.25
```

Generated trajectory:

```text
/home/zhuchao/svin_ws/src/SVIn/pose_graph/svin_results/svin_2026_06_10_19_34_31.txt
/home/zhuchao/svin_ws/src/SVIn/pose_graph/svin_results/svin_2026_06_10_19_34_31.ply
```

Trajectory statistics:

```text
points: 532
duration: 88.488 s
path length: 26.149 m
start/end displacement: 0.258 m
XYZ range: [1.226, 0.981, 0.333] m
median step: 0.0335 m
95% step: 0.1339 m
max step: 0.6090 m
```

Observation:

- This is the current best baseline to keep in the config.
- It no longer shows the extreme kilometer-scale divergence.
- The trajectory is still too compact for a real navigation experiment, so the remaining problem is likely calibration/data quality rather than only ROS2 callback ordering.

## 2026-06-10 Inverse T_SC Experiment

Reason for the experiment:

- OKVIS code comments indicate `T_SC` is sensor/IMU to camera, so both camera matrices were temporarily inverted to test whether the earlier config convention was reversed.

Run command:

```bash
source /opt/ros/humble/setup.bash
source /home/zhuchao/svin_ws/install/setup.bash
ROS_LOG_DIR=/tmp/ros_logs_svin ros2 launch okvis_ros svin_zed_20260610_rviz.launch.py bag_rate:=0.25
```

Generated trajectory:

```text
/home/zhuchao/svin_ws/src/SVIn/pose_graph/svin_results/svin_2026_06_10_19_43_14.txt
/home/zhuchao/svin_ws/src/SVIn/pose_graph/svin_results/svin_2026_06_10_19_43_14.ply
```

Trajectory statistics:

```text
points: 785
duration: 88.354 s
path length: 9683.365 m
start/end displacement: 9625.851 m
XYZ range: [5687.076, 7508.945, 1984.377] m
median step: 9.9476 m
95% step: 35.6514 m
max step: 224.9625 m
```

Observation:

- The inverse-`T_SC` trial diverged badly and is not usable.
- The config was reverted to the 19:34 baseline convention after this test.
- During shutdown, `pose_graph_node` saved the txt/ply files and then aborted; the result files above were already written.

## Current Improvement Direction

Keep these changes:

- `stereo_sync.cpp` synchronized-header publishing fix.
- `okvis_node.cpp` single-threaded executor.
- `config_zed_stereo_20260610.yaml` optical-frame baseline that produced `svin_2026_06_10_19_34_31.txt`.

Recommended next work:

- Preprocess the 20260610 bag into a smaller synchronized bag: convert `bgra8` 1920x1080 images to `mono8` or `bgr8`, resize to 960x540, publish `/cam0/image_raw` and `/cam1/image_raw` with a common timestamp, and order messages by header time.
- Record or estimate the real experiment path length/shape so the trajectory can be judged against ground truth instead of only against smoothness.
- Run a dedicated Kalibr camera-IMU calibration for this exact ZED+IMU setup, including time offset, instead of mixing Kalibr stereo intrinsics with the ZED built-in left-camera-to-IMU TF.
- Collect a cleaner calibration/navigation bag with 10-20 seconds static start, slower motion, good texture, and `/tf_static` plus camera info topics recorded.

## 2026-06-10 RViz Yellow Trajectory Check

Run command:

```bash
source /opt/ros/humble/setup.bash
source /home/zhuchao/svin_ws/install/setup.bash
ROS_LOG_DIR=/tmp/ros_logs_svin ros2 launch okvis_ros svin_zed_20260610_rviz.launch.py bag_rate:=0.25
```

Generated trajectory:

```text
/home/zhuchao/svin_ws/src/SVIn/pose_graph/svin_results/svin_2026_06_10_19_55_52.txt
/home/zhuchao/svin_ws/src/SVIn/pose_graph/svin_results/svin_2026_06_10_19_55_52.ply
```

Trajectory statistics:

```text
points: 476
duration: 88.758 s
path length: 23.043 m
start/end displacement: 0.144 m
XYZ range: [1.174, 0.743, 0.294] m
median step: 0.0352 m
95% step: 0.1274 m
max step: 0.4394 m
```

RViz trajectory colors:

- Yellow path is `/okvis_path`, the raw/current OKVIS VIO trajectory.
- Green path is `/loop_closure_path`, the pose-graph/loop-closure trajectory.

Observation:

- The yellow path is not a ground-truth/reference path. It is the frontend VIO estimate.
- During this run the terminal repeatedly reported `Received image from the past`, `Dropping frame`, and `Frame delayed` in the early/middle part of the bag.
- The saved result did not diverge like the inverse-`T_SC` test, but the trajectory is still very compact. If the real experiment path was much larger than about 1-2 m in XY extent, the remaining issue is not only display offset; the frontend scale/pose estimate is still not adapted well enough.

## 2026-06-10 20:26 Raw Bag Rerun

Run command:

```bash
source /opt/ros/humble/setup.bash
source /home/zhuchao/svin_ws/install/setup.bash
ROS_LOG_DIR=/tmp/ros_logs_svin ros2 launch okvis_ros svin_zed_20260610_rviz.launch.py bag_rate:=0.25
```

Generated trajectory:

```text
/home/zhuchao/svin_ws/src/SVIn/pose_graph/svin_results/svin_2026_06_10_20_26_45.txt
/home/zhuchao/svin_ws/src/SVIn/pose_graph/svin_results/svin_2026_06_10_20_26_45.ply
```

Trajectory statistics:

```text
points: 510
duration: 88.019 s
path length: 21.839 m
start/end displacement: 0.052 m
XYZ range: [0.863, 0.644, 0.322] m
median step: 0.0338 m
95% step: 0.1098 m
max step: 0.2817 m
```

Observation:

- The run completed and saved a valid trajectory.
- It still reported repeated `Received image from the past`, `Dropping frame`, and `Frame delayed` messages in multiple parts of the bag.
- The output is more compact than the 19:34 and 19:55 runs. This again points to an input/calibration/scale issue rather than an RViz display problem.
- Next improvement should use a preprocessed SVIn bag instead of rerunning the original `bgra8 1920x1080` bag.
