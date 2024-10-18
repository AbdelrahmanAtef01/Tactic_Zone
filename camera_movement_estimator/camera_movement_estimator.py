import cv2
import numpy as np
import sys 
sys.path.append('../')
from utils import measure_distance,measure_xy_distance

class CameraMovementEstimator():
    def __init__(self, frame):
        self.minimum_distance = 5

        self.lk_params = dict(
            winSize = (15, 15),
            maxLevel = 2,
            criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03)
        )

        first_frame_grayscale = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mask_features = np.zeros_like(first_frame_grayscale)
        mask_features[:, 0:20] = 1
        mask_features[:, 900:1050] = 1

        self.features = dict(
            maxCorners = 100,
            qualityLevel = 0.3,
            minDistance = 3,
            blockSize = 7,
            mask = mask_features
        )

    def add_adjust_positions_to_tracks(self, tracks, camera_movement_per_frame):
        for object, object_tracks in tracks.items():
            for frame_num, track in enumerate(object_tracks):
                for track_id, track_info in track.items():
                    if object != 'ball':
                        position = track_info['position']
                        camera_movement = camera_movement_per_frame[frame_num]
                        if camera_movement:
                            position_adjusted = (position[0] - camera_movement[0], position[1] - camera_movement[1])
                        else:
                            position_adjusted = (position[0] , position[1])
                        tracks[object][frame_num][track_id]['position_adjusted'] = position_adjusted
                    else:
                        # Check if 'position' exists for the current frame
                        if 'position' in tracks[object][frame_num][track_id]:
                            # Use the current frame's position
                            tracks[object][frame_num][track_id]['position_adjusted'] = tracks[object][frame_num][track_id]['position']
                        elif frame_num > 0 and 'position' in tracks[object][frame_num - 1][track_id]:
                            tracks[object][frame_num][track_id]['position_adjusted'] = tracks[object][frame_num - 1][track_id]['position']
                        else:
                            # Fallback to the default (0, 0)
                            tracks[object][frame_num][track_id]['position_adjusted'] = (0, 0)  

    def get_camera_movement(self, frames):
        camera_movement = [[0, 0]] * len(frames)

        old_gray = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY)
        old_features = cv2.goodFeaturesToTrack(old_gray, **self.features)

        if old_features is None or len(old_features) == 0:
            return camera_movement

        for frame_num in range(1, len(frames)):
            frame_gray = cv2.cvtColor(frames[frame_num], cv2.COLOR_BGR2GRAY)
            
            # Ensure old_features has valid points
            if old_features is None or len(old_features) == 0:
                old_features = cv2.goodFeaturesToTrack(frame_gray, **self.features)
                if old_features is None:
                    continue

            # Compute optical flow
            new_features, status, _ = cv2.calcOpticalFlowPyrLK(old_gray, frame_gray, old_features, None, **self.lk_params)

            if new_features is None:
                continue

            max_distance = 0
            camera_movement_x, camera_movement_y = 0, 0

            for i, (new, old) in enumerate(zip(new_features, old_features)):
                if status[i]:  # Only process points with valid status
                    new_features_point = new.ravel()
                    old_features_point = old.ravel()

                    distance = measure_distance(new_features_point, old_features_point)
                    if distance > max_distance:
                        max_distance = distance
                        camera_movement_x, camera_movement_y = measure_xy_distance(old_features_point, new_features_point)

            if max_distance > self.minimum_distance:
                camera_movement[frame_num] = [camera_movement_x, camera_movement_y]
                old_features = cv2.goodFeaturesToTrack(frame_gray, **self.features)

            old_gray = frame_gray.copy()

        return camera_movement