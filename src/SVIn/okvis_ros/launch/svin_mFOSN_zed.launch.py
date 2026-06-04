from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
import os


def launch_setup(context, *args, **kwargs):
    pkg_share = FindPackageShare('okvis_ros').perform(context)
    okvis_config_raw = LaunchConfiguration('okvis_config').perform(context)

    if os.path.isabs(okvis_config_raw):
        abs_config_path = okvis_config_raw
    else:
        abs_config_path = os.path.join(pkg_share, 'config', okvis_config_raw)

    print(f"\n[INFO] SVIn config: {abs_config_path}\n")

    # stereo_sync: 同步双目图像时间戳
    # ZED 输出原始未压缩图像 → compressed=False
    stereo_sync_node = Node(
        package='okvis_ros',
        executable='stereo_sync',
        name='stereo_sync',
        output='screen',
        parameters=[{
            'config_filename': abs_config_path,
            'left_img_topic': '/zed/zed_node/left/color/raw/image',
            'right_img_topic': '/zed/zed_node/right/color/raw/image',
            'compressed': False           # ZED 输出原始图，非压缩图
        }]
    )

    # okvis_node: VIO 前端 + Ceres 优化后端
    okvis_node = Node(
        package='okvis_ros',
        executable='okvis_node',
        name='okvis_node',
        parameters=[{
            'config_filename': abs_config_path,
            'mesh_file': 'firefly.dae'
        }],
        remappings=[
            ('/camera0', '/cam0/image_raw'),
            ('/camera1', '/cam1/image_raw'),
            ('/imu', '/imu')
        ]
    )

    # pose_graph_node: 回环检测 + 位姿图优化
    pose_graph_node = Node(
        package='pose_graph',
        executable='pose_graph_node',
        name='pose_graph_node',
        parameters=[{
            'config_file': abs_config_path
        }]
    )

    # rviz2: 可视化
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz',
        arguments=['-d', os.path.join(pkg_share, 'rviz_config', 'svin.rviz')],
        output='screen'
    )

    return [stereo_sync_node, okvis_node, pose_graph_node, rviz_node]


def generate_launch_description():
    config_arg = DeclareLaunchArgument(
        'okvis_config',
        default_value='config_mFOSN_zed.yaml',
        description='SVIn config YAML (absolute path or filename under config/)'
    )

    return LaunchDescription([
        config_arg,
        OpaqueFunction(function=launch_setup)
    ])
