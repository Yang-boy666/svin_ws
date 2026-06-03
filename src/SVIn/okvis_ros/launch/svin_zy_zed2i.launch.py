from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
import os


def launch_setup(context, *args, **kwargs):
    # 用 FindPackageShare 找到 install 目录下的 config
    pkg_share = FindPackageShare('okvis_ros').perform(context)
    okvis_config_raw = LaunchConfiguration('okvis_config').perform(context)
    # 可能是绝对路径（命令行传入），也可能是配置文件名（默认）
    if os.path.isabs(okvis_config_raw):
        abs_okvis_config_path = okvis_config_raw
    else:
        abs_okvis_config_path = os.path.join(pkg_share, 'config', okvis_config_raw)

    print(f"\n[INFO] Full path to okvis_config: {abs_okvis_config_path}\n")

    # stereo_sync 节点（同步和解压左右相机）
    stereo_sync_node = Node(
        package='okvis_ros',
        executable='stereo_sync',
        name='stereo_sync',
        output='screen',
        parameters=[{
            'config_filename': abs_okvis_config_path,
            'left_img_topic': '/zed/zed_node/left/color/raw/image',
            'right_img_topic': '/zed/zed_node/right/color/raw/image',
            'compressed': True
        }]
    )

    # OKVIS 节点（VIO 前端）
    okvis_node = Node(
        package='okvis_ros',
        executable='okvis_node',
        name='okvis_node',
        parameters=[{
            'config_filename': abs_okvis_config_path,
            'mesh_file': 'firefly.dae'
        }],
        remappings=[
            ('/camera0', '/zed/zed_node/left/color/raw/image'),
            ('/camera1', '/zed/zed_node/right/color/raw/image'),
            ('/imu', '/imu_mFOSN')
        ]
    )

    # Pose Graph 节点（后端回环检测）
    pose_graph_node = Node(
        package='pose_graph',
        executable='pose_graph_node',
        name='pose_graph_node',
        parameters=[{
            'config_file': abs_okvis_config_path
        }]
    )

    # RViz2 节点（可视化）
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz',
        arguments=['-d', os.path.join(pkg_share, 'rviz_config', 'svin.rviz')],
        output='screen'
    )

    return [stereo_sync_node, okvis_node, pose_graph_node, rviz_node]


def generate_launch_description():
    # 声明 YAML 配置参数
    # 默认值为 config_zy.yaml，会自动在 install/share/okvis_ros/config/ 下查找
    # 也可从命令行传入绝对路径：ros2 launch ... okvis_config:=/absolute/path/to/config.yaml
    config_arg = DeclareLaunchArgument(
        'okvis_config',
        default_value='config_zy.yaml'
    )

    return LaunchDescription([
        config_arg,
        OpaqueFunction(function=launch_setup)
    ])
