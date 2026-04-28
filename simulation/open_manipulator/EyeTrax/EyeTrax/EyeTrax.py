import argparse
import sys

sys.path.append('/root/ros2_ws/src/open_manipulator/EyeTrax/src')

from eyetrax.app.demo import run_demo

def main():
    args = argparse.Namespace(
                filter='none',
                ema_alpha=0.25,
                camera=5,
                calibration='dense',
                grid_rows=5,
                grid_cols=5,
                grid_margin=0.1,
                background=None, 
                confidence=0.9, 
                model='ridge', 
                model_file=None
            )

    run_demo(args)