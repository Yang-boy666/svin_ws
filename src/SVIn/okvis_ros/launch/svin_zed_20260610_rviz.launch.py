from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, OpaqueFunction, TimerAction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
import os


def launch_setup(context, *args, **kwargs):
    pkg_share = FindPackageShare('okvis_ros').perform(context)

    config_raw = LaunchConfiguration('config_file').perform(context)
    rviz_config_raw = LaunchConfiguration('rviz_config').perform(context)

    if os.path.isabs(config_raw):
        config_path = config_raw
    else:
        config_path = os.path.join(pkg_share, 'config', config_raw)

    if os.path.isabs(rviz_config_raw):
        rviz_config_path = rviz_config_raw
    else:
        rviz_config_path = os.path.join(pkg_share, 'rviz_config', rviz_config_raw)

    left_img_topic = LaunchConfiguration('left_img_topic')
    right_img_topic = LaunchConfiguration('right_img_topic')
    imu_topic = LaunchConfiguration('imu_topic')

    print(f"\n[INFO] SVIn config: {config_path}")
    print(f"[INFO] RViz config: {rviz_config_path}\n")

    stereo_sync_node = Node(
        package='okvis_ros',
        executable='stereo_sync',
        name='stereo_sync',
        output='screen',
        parameters=[{
            'config_filename': config_path,
            'left_img_topic': left_img_topic,
            'right_img_topic': right_img_topic,
            'compressed': False,
        }],
        additional_env={'ROS_LOG_DIR': '/tmp/ros_logs_svin'},
    )

    okvis_node = Node(
        package='okvis_ros',
        executable='okvis_node',
        name='okvis_node',
        output='screen',
        parameters=[{
            'config_filename': config_path,
            'mesh_file': 'firefly.dae',
        }],
        remappings=[
            ('/camera0', '/cam0/image_raw'),
            ('/camera1', '/cam1/image_raw'),
            ('/imu', imu_topic),
        ],
        additional_env={'ROS_LOG_DIR': '/tmp/ros_logs_svin'},
    )

    pose_graph_node = Node(
        package='pose_graph',
        executable='pose_graph_node',
        name='pose_graph_node',
        output='screen',
        parameters=[{
            'config_file': config_path,
        }],
        additional_env={'ROS_LOG_DIR': '/tmp/ros_logs_svin'},
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz',
        output='screen',
        arguments=['-d', rviz_config_path],
        additional_env={'ROS_LOG_DIR': '/tmp/ros_logs_svin'},
    )

    bag_player = TimerAction(
        period=LaunchConfiguration('bag_start_delay'),
        actions=[
            ExecuteProcess(
                condition=IfCondition(LaunchConfiguration('play_bag')),
                cmd=[
                    'ros2',
                    'bag',
                    'play',
                    LaunchConfiguration('bag_path'),
                    '--rate',
                    LaunchConfiguration('bag_rate'),
                    '--read-ahead-queue-size',
                    LaunchConfiguration('read_ahead_queue_size'),
                ],
                output='screen',
                additional_env={'ROS_LOG_DIR': '/tmp/ros_logs_svin'},
            )
        ],
    )

    return [stereo_sync_node, okvis_node, pose_graph_node, rviz_node, bag_player]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'config_file',
            default_value='/home/zhuchao/svin_ws/src/SVIn/config/config_zed_stereo_20260610.yaml',
            description='SVIn config YAML, absolute path or filename under okvis_ros/config.',
        ),
        DeclareLaunchArgument(
            'rviz_config',
            default_value='svin.rviz',
            description='RViz config, absolute path or filename under okvis_ros/rviz_config.',
        ),
        DeclareLaunchArgument(
            'left_img_topic',
            default_value='/zed/zed_node/left/color/raw/image',
            description='Left image topic from ZED/bag.',
        ),
        DeclareLaunchArgument(
            'right_img_topic',
            default_value='/zed/zed_node/right/color/raw/image',
            description='Right image topic from ZED/bag.',
        ),
        DeclareLaunchArgument(
            'imu_topic',
            default_value='/zed/zed_node/imu/data_raw',
            description='IMU topic from ZED/bag.',
        ),
        DeclareLaunchArgument(
            'play_bag',
            default_value='true',
            description='Whether this launch file should also play the ROS2 bag.',
        ),
        DeclareLaunchArgument(
            'bag_path',
            default_value='/media/zhuchao/My Book/zy jetson/数据集/20260610/20260610双目标定数据',
            description='ROS2 bag directory to play when play_bag is true.',
        ),
        DeclareLaunchArgument(
            'bag_rate',
            default_value='0.5',
            description='Bag playback rate. 0.5 is gentler for this large 18.5 GiB bag.',
        ),
        DeclareLaunchArgument(
            'read_ahead_queue_size',
            default_value='5000',
            description='ros2 bag play read-ahead queue size.',
        ),
        DeclareLaunchArgument(
            'bag_start_delay',
            default_value='3.0',
            description='Seconds to wait before starting ros2 bag play.',
        ),
        OpaqueFunction(function=launch_setup),
    ])
