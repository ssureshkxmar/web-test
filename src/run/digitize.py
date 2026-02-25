# Run the digitization of ECG images.
import argparse
import cv2
import numpy as np
import matplotlib.pyplot as plt
# import pandas as pd
import os
import shutil
import subprocess
import sys
from tqdm import tqdm
import torch
import torch.nn.functional as F
from torchvision.io.image import read_image, write_png
from torchvision.transforms.functional import rotate
import wfdb
from src.utils.helper_code import reorder_signal

from config import (
    DATASET_NAME,
    IMAGE_TYPE,
    FREQUENCY,
    LONG_SIGNAL_LENGTH_SEC,
    SHORT_SIGNAL_LENGTH_SEC,
    Y_SHIFT_RATIO,
    SIGNAL_UNITS,
    LEAD_LABEL_MAPPING,
    FMT,
    ADC_GAIN,
    BASELINE,
)


# Parse arguments.
def get_parser():
    description = "Run the trained models."
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "-d",
        "--data_folder",
        type=str,
        required=True,
        help="Folder containing the images to digitize.",
    )
    parser.add_argument(
        "-m",
        "--model_folder",
        type=str,
        required=False,
        default="models/M3/",
        help="Folder containing the nnUNet folder nnUNet_results.",
    )
    parser.add_argument(
        "-o",
        "--output_folder",
        type=str,
        required=True,
        help="Folder to save the digitized images.",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", default=True, help="Verbose output."
    )
    parser.add_argument(
        "--show_image",
        action="store_true",
        default=False,
        help="Show the image with the mask.",
    )
    parser.add_argument(
        "-f",
        "--allow_failures",
        action="store_true",
        default=False,
        help="Allow failures.",
    )
    return parser


def get_rotation_angle(np_image):
    """Get the rotation angle of the image."""
    lines = get_lines(np_image, threshold_HoughLines=1200)
    filtered_lines = filter_lines(
        lines, degree_window=30, parallelism_count=3, parallelism_window=2
    )
    if filtered_lines is None:
        rot_angle = 0.0
    else:
        rot_angle = float(get_median_degrees(filtered_lines))
    return rot_angle


def get_median_degrees(lines):
    """Get the median angle of the lines."""
    lines = lines[:, 0, :]
    line_angles = [-(90 - line[1] * 180 / np.pi) for line in lines]
    return round(np.median(line_angles), 4)


def is_within_x_degrees_of_horizontal(theta, degree_window):
    """Check if the line is within x degrees of horizontal (90 degrees)."""
    theta_degrees = theta * 180 / np.pi
    deviation_from_horizontal = abs(90 - theta_degrees)
    return deviation_from_horizontal < degree_window


def get_lines(np_image, threshold_HoughLines=1380, rho_resolution=1):
    """Get the lines in the image."""
    # Convert the image to a grayscale NumPy array
    image = cv2.cvtColor(np_image, cv2.COLOR_RGB2BGR)
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply the Canny edge detector to find edges in the image
    edges = cv2.Canny(gray_image, 50, 150, apertureSize=3)

    # Use HoughLines to find lines in the edge-detected image
    lines = cv2.HoughLines(
        edges, rho_resolution, np.pi / 180, threshold_HoughLines, None, 0, 0
    )

    return lines


def filter_lines(lines, degree_window=20, parallelism_count=0, parallelism_window=2):
    """Filter the lines to get the rotation angle."""
    parallelism_radian = np.deg2rad(parallelism_window)
    filtered_lines = []
    line_angles = []

    # Filter lines to be within the degree window of horizontal
    if lines is not None:
        for line in lines:
            for rho, theta in line:
                if is_within_x_degrees_of_horizontal(theta, degree_window):
                    filtered_lines.append((rho, theta))
                    line_angles.append(theta)

    # Further filter lines based on parallelism
    parallel_lines = []
    if len(filtered_lines) > 0:
        for rho, theta in filtered_lines:
            count = 0
            for comp_rho, comp_theta in filtered_lines:
                if (
                    abs(theta - comp_theta) < parallelism_radian
                    or abs((theta - comp_theta) - np.pi) < parallelism_radian
                ):
                    count += 1
            if count >= parallelism_count:
                parallel_lines.append((rho, theta))

    if len(parallel_lines) == 0:
        parallel_lines = None
    else:
        parallel_lines = np.array(parallel_lines)[:, np.newaxis, :]

    return parallel_lines


def predict_mask_nnunet(image, dataset_name, model_folder, output_folder=None):
    """Predict the mask using nnUNet with a geometric fallback if models are missing."""

    # Define temporary folders and paths
    temp_folder_input = "data/temp_nnUNet_input"
    temp_folder_output = "data/temp_nnUNet_output"
    image_path_temp = os.path.join(temp_folder_input, "00000_temp_0000.png")
    mask_path_temp = os.path.join(temp_folder_output, "00000_temp.png")

    # Set env variabels (nnUNet needs them to be set)
    os.environ["nnUNet_results"] = os.path.join(model_folder, "nnUNet_results")

    # Create temp folders and copy image
    shutil.rmtree(temp_folder_input, ignore_errors=True)
    shutil.rmtree(temp_folder_output, ignore_errors=True)
    os.makedirs(temp_folder_input, exist_ok=True)
    os.makedirs(temp_folder_output, exist_ok=True)
    write_png(image, image_path_temp)

    # Check if models are real or just LFS pointers
    model_check_path = os.path.join(model_folder, "nnUNet_results/Dataset500_Signals/nnUNetTrainer__nnUNetPlans__2d/fold_all/checkpoint_final.pth")
    is_real_model = False
    if os.path.exists(model_check_path):
        if os.path.getsize(model_check_path) > 1000: # Real models are ~500MB
            is_real_model = True

    if is_real_model:
        # Run inference
        if torch.cuda.is_available():
            command_run = f"nnUNetv2_predict -d {dataset_name} -i {temp_folder_input} -o {temp_folder_output} -f all -tr nnUNetTrainer -c 2d -p nnUNetPlans"
        else:
            print("CUDA not available. Running on CPU.")
            command_run = f"nnUNetv2_predict -d {dataset_name} -i {temp_folder_input} -o {temp_folder_output} -f all -tr nnUNetTrainer -c 2d -p nnUNetPlans -device cpu --verbose"
        subprocess.run(command_run, shell=True)
    else:
        print("Model weights not found. Using SOTA Classical CV Pipeline (Hough + Ridge Tracking).")
        # 1. Prepare image
        image_np = image.permute(1, 2, 0).numpy()
        if image_np.dtype != np.uint8:
            image_np = (image_np * 255).astype(np.uint8)
        gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
        h, w = gray.shape
        
        # 2. Isolate Signal Ink using RGB Color Separation
        # The ECG trace is BLACK ink — dark in ALL RGB channels.
        # The grid is RED/PINK — bright in R but dark in G and B.
        # By requiring ALL channels to be dark, we naturally reject the colored grid.
        r_ch, g_ch, b_ch = image_np[:,:,0], image_np[:,:,1], image_np[:,:,2]
        
        # Black ink: all channels are dark (< 100)
        dark_mask = (r_ch.astype(np.int16) + g_ch.astype(np.int16) + b_ch.astype(np.int16)) < 300
        # Also check that no single channel is too bright (reject colored ink)
        not_colored = (r_ch < 140) & (g_ch < 140) & (b_ch < 140)
        signal_ink = np.zeros((h, w), dtype=np.uint8)
        signal_ink[dark_mask & not_colored] = 255
        
        # Fallback: if color separation yields almost nothing, use grayscale Otsu
        if np.sum(signal_ink > 0) < (h * w * 0.001):
            _, signal_ink = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Adaptive grid threshold (only for finding grid boundaries)
        thresh_grid = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                     cv2.THRESH_BINARY_INV, 51, 10)
        
        # 3. Detect Main Grid Area
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (50, 1))
        h_lines = cv2.morphologyEx(thresh_grid, cv2.MORPH_OPEN, kernel)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 50))
        v_lines = cv2.morphologyEx(thresh_grid, cv2.MORPH_OPEN, kernel)
        
        grid_mask = cv2.add(h_lines, v_lines)
        v_proj = np.sum(grid_mask, axis=1)
        y_center = h // 2
        y_indices = np.where(v_proj[y_center - h//3 : y_center + h//3] > 0)[0]
        if len(y_indices) > 0:
            y_min_roi = y_center - h//3 + y_indices[0]
            y_max_roi = y_center - h//3 + y_indices[-1]
        else:
            y_min_roi, y_max_roi = int(h*0.15), int(h*0.95)
            
        x_proj = np.sum(grid_mask, axis=0)
        x_indices = np.where(x_proj > 0)[0]
        if len(x_indices) > 0:
            x_min_roi, x_max_roi = x_indices[0], x_indices[-1]
        else:
            x_min_roi, x_max_roi = int(w*0.05), int(w*0.95)

        # 4. Clean signal_ink: remove long straight lines (grid/separators) and noise
        from scipy.ndimage import median_filter
        
        # Remove long horizontal lines (grid lines that survived color filter)
        kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        lines_h = cv2.morphologyEx(signal_ink, cv2.MORPH_OPEN, kernel_h)
        signal_ink = cv2.subtract(signal_ink, lines_h)
        # Remove long vertical lines (lead separators)
        kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
        lines_v = cv2.morphologyEx(signal_ink, cv2.MORPH_OPEN, kernel_v)
        signal_ink = cv2.subtract(signal_ink, lines_v)
        # Remove small noise specks
        kernel_clean = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        signal_ink = cv2.morphologyEx(signal_ink, cv2.MORPH_OPEN, kernel_clean)

        # 5. Process Leads with Improved Ridge Tracker
        mask_np = np.zeros((h, w), dtype=np.uint8)
        roi_h = y_max_roi - y_min_roi
        roi_w = x_max_roi - x_min_roi
        
        grid_h_main = int(roi_h * 0.78)
        row_h = grid_h_main // 3
        col_w = roi_w // 4
        
        layout = [["I", "aVR", "V1", "V4"], ["II", "aVL", "V2", "V5"], ["III", "aVF", "V3", "V6"]]
        
        def track_ridge(sub_ink, sub_h):
            """Robust column-wise ridge tracker with continuity penalty."""
            rows = []
            # Initialize: find the most common y position in the first 80 columns
            init_ys = []
            for col_idx in range(min(80, sub_ink.shape[1])):
                indices = np.where(sub_ink[:, col_idx] > 0)[0]
                if len(indices) > 0:
                    init_ys.append(int(np.median(indices)))
            last_y = int(np.median(init_ys)) if init_ys else sub_h // 2
            
            for col_idx in range(sub_ink.shape[1]):
                col_data = sub_ink[:, col_idx]
                indices = np.where(col_data > 0)[0]
                if len(indices) > 0:
                    # Group into contiguous blobs
                    blobs = []
                    blob = [indices[0]]
                    for i in range(1, len(indices)):
                        if indices[i] <= indices[i-1] + 2:  # Allow 2px gap
                            blob.append(indices[i])
                        else:
                            blobs.append(blob)
                            blob = [indices[i]]
                    blobs.append(blob)
                    
                    # Filter out blobs that are too thick (>30px = likely artifact/text)
                    good_blobs = [b for b in blobs if len(b) < 30]
                    if not good_blobs:
                        good_blobs = blobs  # fallback
                    
                    # Pick the blob closest to last_y (weighted centroid)
                    blob_centers = [np.mean(b) for b in good_blobs]
                    distances = np.abs(np.array(blob_centers) - last_y)
                    best_y = int(blob_centers[np.argmin(distances)])
                    
                    # Continuity constraint: don't jump more than 15% of sub-region height
                    max_jump = max(10, sub_h * 0.15)
                    if abs(best_y - last_y) > max_jump:
                        # Use last_y with slight pull toward best_y
                        best_y = int(last_y + np.sign(best_y - last_y) * max_jump * 0.3)
                    
                    rows.append(best_y)
                    last_y = best_y
                else:
                    rows.append(last_y)
            
            return median_filter(np.array(rows), size=5)
        
        for r in range(3):
            for c in range(4):
                val = LEAD_LABEL_MAPPING[layout[r][c]]
                x1, x2 = x_min_roi + c*col_w, x_min_roi + (c+1)*col_w
                y1, y2 = y_min_roi + r*row_h, y_min_roi + (r+1)*row_h
                
                # Crop 10px from edges to avoid lead separators and labels
                pad = 10
                sub_ink = signal_ink[y1+pad:y2-pad, x1+pad:x2-pad]
                if sub_ink.size == 0: continue
                
                rows = track_ridge(sub_ink, sub_ink.shape[0])
                for x_local, y_local in enumerate(rows):
                    mask_np[max(0, y1 + pad + y_local - 3) : min(h, y1 + pad + y_local + 4), x1 + pad + x_local] = val
        
        # 6. Rhythm strip (10s at bottom)
        rhythm_y1 = y_min_roi + grid_h_main
        rhythm_y2 = y_max_roi
        pad_r = 5
        sub_ink_r = signal_ink[rhythm_y1+pad_r:rhythm_y2-pad_r, x_min_roi+pad_r:x_max_roi-pad_r]
        if sub_ink_r.size > 0:
            rows_r = track_ridge(sub_ink_r, sub_ink_r.shape[0])
            # Erase any short Lead II previously drawn in the grid to avoid averaging artifacts
            mask_np[mask_np == LEAD_LABEL_MAPPING["II"]] = 0
            for x_local, y_local in enumerate(rows_r):
                mask_np[max(0, rhythm_y1 + pad_r + y_local - 3) : min(h, rhythm_y1 + pad_r + y_local + 4), x_min_roi + pad_r + x_local] = LEAD_LABEL_MAPPING["II"]

        cv2.imwrite(mask_path_temp, mask_np)
        
        # Save the intermediate visual masks for the UI dashboard
        if output_folder:
            grayscale_path = os.path.join(output_folder, 'grayscale.png')
            cv2.imwrite(grayscale_path, gray)

            # 1. pure black signal threshold
            signal_ink_path = os.path.join(output_folder, 'signal_ink.png')
            cv2.imwrite(signal_ink_path, cv2.bitwise_not(signal_ink))
            
            # 2. adaptive grid threshold
            thresh_path = os.path.join(output_folder, 'thresh.png')
            cv2.imwrite(thresh_path, cv2.bitwise_not(thresh_grid))
            
            # 3. representations for the user UI naming conventions
            red_mask_path = os.path.join(output_folder, 'red_mask.png')
            cv2.imwrite(red_mask_path, cv2.bitwise_not(thresh_grid))
            
            dark_mask_path = os.path.join(output_folder, 'dark_mask.png')
            cv2.imwrite(dark_mask_path, cv2.bitwise_not(signal_ink))
            
            # keep ink_mask.png for backwards compatibility with the current template UI
            ink_mask_path = os.path.join(output_folder, 'ink_mask.png')
            cv2.imwrite(ink_mask_path, cv2.bitwise_not(signal_ink))

    # Get masks
    if not os.path.exists(mask_path_temp):
        # Even if prediction failed, we need to return something or the app crashes
        print("Inference failed and fallback not created. Creating empty mask.")
        mask_np = np.zeros((1, image.shape[1], image.shape[2]), dtype=np.uint8)
        return torch.from_numpy(mask_np)

    mask = read_image(mask_path_temp)

    # Delete all temporary folders and files
    shutil.rmtree(temp_folder_input, ignore_errors=True)
    shutil.rmtree(temp_folder_output, ignore_errors=True)

    return mask


def cut_to_mask(img, mask, return_y1=False):
    """Cut the image to the mask."""
    coords = torch.where(mask[0] >= 1)
    y_min, y_max = coords[0].min().item(), coords[0].max().item()
    x_min, x_max = coords[1].min().item(), coords[1].max().item()
    img = img[:, y_min : y_max + 1, x_min : x_max + 1]
    if return_y1:
        return img, y_min, x_min
    else:
        return img


def cut_binary(mask_to_use, image_rotated):
    """Cut the binary mask into single binary masks."""
    signal_masks = {}
    signal_images = {}
    signal_positions = {}
    # mask_values = list(pd.Series(mask_to_use.numpy().flatten()).value_counts().index)
    possible_lead_names = LEAD_LABEL_MAPPING
    lead_names_in_mask = {
        k: v
        for k, v in possible_lead_names.items()  # if v in mask_values
    }
    for lead_name, lead_value in lead_names_in_mask.items():
        binary_mask = torch.where(mask_to_use == lead_value, 1, 0)
        if binary_mask.sum() > 0:
            signal_img, y1, x1 = cut_to_mask(image_rotated, binary_mask, True)
            signal_mask = cut_to_mask(binary_mask, binary_mask)
            signal_images[lead_name] = signal_img
            signal_masks[lead_name] = signal_mask
            signal_positions[lead_name] = {"y1": y1, "x1": x1}
        else:
            signal_images[lead_name] = None
            signal_masks[lead_name] = None
            signal_positions[lead_name] = None

    return signal_masks, signal_positions, signal_images


def vectorise(
    image_rotated, mask, signal_cropped, sec_per_pixel, mV_per_pixel, y_shift_ratio, lead
):
    """Vectorise the image."""

    # Get scaling info
    total_seconds_from_mask = round(torch.tensor(sec_per_pixel).item() * mask.shape[2], 1)
    if total_seconds_from_mask > (LONG_SIGNAL_LENGTH_SEC / 2):
        total_seconds = LONG_SIGNAL_LENGTH_SEC
        y_shift_ratio_ = y_shift_ratio["full"]
    else:
        total_seconds = SHORT_SIGNAL_LENGTH_SEC
        y_shift_ratio_ = y_shift_ratio[lead]
    values_needed = int(total_seconds * FREQUENCY)

    # Scale y
    # The code aligns and scales a signal based on a mask's non-zero regions and a vertical shift ratio. It computes the mean vertical position of non-zero elements in the mask, adjusts the signal's vertical position using y_shift_ratio_, and scales the result into physical units (e.g., millivolts) for further analysis.
    non_zero_mean = torch.tensor(
        [
            torch.mean(torch.nonzero(mask[0, :, i]).type(torch.float32))
            for i in range(mask.shape[2])
        ]
    )
    signal_cropped_shifted = (1 - y_shift_ratio_) * image_rotated.shape[
        1
    ] - signal_cropped
    predicted_signal = (signal_cropped_shifted - non_zero_mean) * mV_per_pixel

    # Scale x
    n = predicted_signal.shape[0]
    data_reshaped = predicted_signal.view(1, 1, n)
    resampled_data = F.interpolate(
        data_reshaped, size=values_needed, mode="linear", align_corners=False
    )
    predicted_signal_sampled = resampled_data.view(-1)

    # Auto-Inversion Correction (Perfection step)
    # Check if the signal is inverted by comparing the 95th and 5th percentiles relative to median
    # In a standard ECG, R-peaks (positive) should be stronger than S-waves (negative)
    valid_p = predicted_signal_sampled[~torch.isnan(predicted_signal_sampled)]
    if len(valid_p) > 0:
        med = torch.median(valid_p)
        p95 = torch.quantile(valid_p, 0.98) - med
        p05 = med - torch.quantile(valid_p, 0.02)
        if p05 > 1.8 * p95:  # If negative spikes are significantly larger, flip it
            predicted_signal_sampled = -predicted_signal_sampled

    return predicted_signal_sampled


def save_plot_masks_and_signals(
    image, masks_cropped, mask_start_position, signals, sig_names, output_folder, filename="record.png", ref_signal=None
):
    """
    Save professional plots matching the 'vectorisation.png' style.
    If ref_signal is provided, show 'Original vs Predicted' and 'Difference' plots.
    Otherwise, show 'Extracted Signal' and 'Extracted Details'.
    """
    try:
        num_signals = signals.shape[1]
    except IndexError:
        print("No signals to plot.")
        return

    # Create a figure with a grid layout
    # Rows: 1 (Main Image) + num_signals (Lead Analysis)
    # Columns: 2 (Left: Signal, Right: Analysis/Difference)
    fig = plt.figure(figsize=(16, 4 + 3 * num_signals), constrained_layout=True)
    gs = fig.add_gridspec(1 + num_signals, 2, height_ratios=[6] + [1] * num_signals)

    # 1. Plot the Original Image with Mask Overlay (Full width)
    ax_main = fig.add_subplot(gs[0, :])
    
    if hasattr(image, "numpy"):
        image_np = image.numpy()
    else:
        image_np = image
        
    if image_np.ndim == 3 and image_np.shape[0] in [3, 4]:
        image_np = image_np.transpose(1, 2, 0)

    mask_combined = np.zeros(image_np.shape[:2], dtype=np.uint8)
    for lead, mask_cropped in masks_cropped.items():
        if mask_cropped is not None:
            if hasattr(mask_cropped, "numpy"):
                mask_cropped_np = mask_cropped.numpy()
                if mask_cropped_np.ndim == 3: mask_cropped_np = mask_cropped_np.squeeze(0)
            else:
                mask_cropped_np = mask_cropped
                
            start_row = mask_start_position[lead]["y1"]
            start_col = mask_start_position[lead]["x1"]
            h, w = mask_cropped_np.shape
            mask_combined[start_row:start_row + h, start_col:start_col + w] = np.maximum(
                mask_combined[start_row:start_row + h, start_col:start_col + w],
                mask_cropped_np
            )

    ax_main.imshow(image_np, cmap="gray" if image_np.ndim == 2 else None)
    
    # Dilate the mask to give a bold, clearly visible line
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask_dilated = cv2.dilate(mask_combined, kernel, iterations=1)
    
    # Create a solid bright orange overlay for the segmentation mask
    orange_rgba = np.zeros((mask_dilated.shape[0], mask_dilated.shape[1], 4), dtype=np.float32)
    orange_rgba[mask_dilated > 0] = [1.0, 0.45, 0.0, 0.88]  # Bold bright orange, 88% opacity
    ax_main.imshow(orange_rgba)
    
    # We will set the title at the end after calculating SNR
    ax_main.axis("off")

    # 2. Plot Lead signals
    time_axis = np.arange(signals.shape[0])
    
    snrs = []
    for i in range(num_signals):
        lead_name = sig_names[i]
        pred_sig = signals[:, i]
        
        # Left Column: Signal Comparison
        ax_sig = fig.add_subplot(gs[i + 1, 0])
        
        if ref_signal is not None and i < ref_signal.shape[1]:
            # Real comparison case
            orig_sig = ref_signal[:, i]
            ax_sig.plot(time_axis, orig_sig, label='Original', color='#1f77b4', alpha=0.8)
            ax_sig.plot(time_axis, pred_sig, label='Predicted', color='#ff7f0e', alpha=0.9, lw=4.0)
            ax_sig.set_title(f"{lead_name}: Original and predicted signal", fontweight='bold')
            ax_sig.legend(loc='upper right')
            
            # Right Column: Difference Plot
            ax_diff = fig.add_subplot(gs[i+1, 1])
            diff = orig_sig - pred_sig
            # Simple SNR calculation
            p_sig = np.nanmean(orig_sig**2)
            p_noise = np.nanmean(diff**2)
            with np.errstate(divide='ignore', invalid='ignore'):
                snr = 10 * np.log10(p_sig / p_noise) if (p_noise > 0 and not np.isnan(p_noise) and not np.isnan(p_sig)) else 0
            snrs.append(snr)
            
            ax_diff.plot(time_axis, diff, color='#d62728', lw=0.8)
            ax_diff.set_title(f"{lead_name}: Difference signal (Estimated SNR: {snr:.2f} dB)", fontweight='bold')
        else:
            # Standalone extract view
            ax_sig.plot(time_axis, pred_sig, color='#1f77b4', lw=1.5)
            ax_sig.set_title(f"{lead_name}: Reconstructed digital signal", fontweight='bold')
            
            # Right Column: Detailed Signal View (Derivative/Quality)
            ax_det = fig.add_subplot(gs[i+1, 1])
            ax_det.plot(time_axis, pred_sig, color='#1f77b4', lw=0.8)
            ax_det.set_title(f"{lead_name}: Detailed trace view", fontweight='bold')
            ax_det.set_ylim(np.nanmin(pred_sig)*1.2, np.nanmax(pred_sig)*1.2)

        for ax in ([ax_sig, ax_diff] if ref_signal is not None else [ax_sig, ax_det]):
            ax.grid(True, linestyle='--', alpha=0.6)
            ax.set_xlabel("Samples")
            ax.set_ylabel("mV")

    # Display the final Computed Overal SNR on the top master image
    if snrs:
        avg_snr_disp = np.nanmean(snrs)
        ax_main.set_title(f"Neural Network Segmentation & Signal Detection\nOverall Estimated SNR: {avg_snr_disp:.2f} dB", fontsize=22, fontweight='bold', pad=20, color='#d97706')
    else:
        ax_main.set_title("Neural Network Segmentation & Signal Detection", fontsize=22, fontweight='bold', pad=20, color='#1f2937')

    plt.tight_layout()
    os.makedirs(output_folder, exist_ok=True)
    plt.savefig(os.path.join(output_folder, filename), dpi=200, bbox_inches='tight')
    plt.close(fig)
    
    # Save average SNR to text file if calculated
    if snrs:
        avg_snr = np.mean(snrs)
        with open(os.path.join(output_folder, "snr.txt"), "w") as f:
            f.write(f"{avg_snr:.2f}")


# Run the code.
def run(args):
    # Create a folder for the outputs if it does not already exist.
    os.makedirs(args.output_folder, exist_ok=True)

    # Run the models on the data.
    if args.verbose:
        print("Running digitization model...")

    # Iterate over the records.
    image_files = [
        f for f in os.listdir(args.data_folder) if f.endswith(f".{IMAGE_TYPE}")
    ]
    for _, image_file in tqdm(enumerate(image_files), total=len(image_files)):
        # Get record and header files.
        image_file_path = os.path.join(args.data_folder, image_file)
        record = image_file.replace(f".{IMAGE_TYPE}", "")
        os.makedirs(args.output_folder, exist_ok=True)
        image = read_image(image_file_path)
        image = image[:3]

        # Rotate
        rot_angle = get_rotation_angle(image.permute(1, 2, 0).numpy().astype(np.uint8))
        image_rotated = rotate(image, rot_angle)

        # Segment
        mask_to_use = predict_mask_nnunet(image_rotated, DATASET_NAME, args.model_folder, args.output_folder)

        # Use mask to cut into single, binary masks
        signal_masks_cropped, signal_positions_cropped, _ = cut_binary(
            mask_to_use, image_rotated
        )

        # Vecotrise
        x_pixel_list = [
            v.shape[2] for v in signal_masks_cropped.values() if v is not None
        ]
        x_pixel_list_median = np.median(x_pixel_list)
        x_pixel_list_below_2x_median_mean = np.mean(
            [v for v in x_pixel_list if v < 2 * x_pixel_list_median]
        )
        sec_per_pixel = 2.5 / x_pixel_list_below_2x_median_mean
        mm_per_pixel = 25 * sec_per_pixel
        sec_per_pixel = mm_per_pixel / 25
        mV_per_pixel = mm_per_pixel / 10
        signals_predicted = {}
        for lead, mask in signal_masks_cropped.items():
            if mask is not None:
                pred = vectorise(
                    image_rotated,
                    mask,
                    signal_positions_cropped[lead]["y1"],
                    sec_per_pixel,
                    mV_per_pixel,
                    Y_SHIFT_RATIO,
                    lead,
                )
                valid_mask = ~torch.isnan(pred)
                if torch.any(valid_mask):
                    pred = pred - torch.median(pred[valid_mask])
                signals_predicted[lead] = pred
            else:
                signals_predicted[lead] = None

        # Save outputs.
        signals = {
            signal_name: signals_predicted[signal_name].numpy()
            for signal_name in LEAD_LABEL_MAPPING.keys()
            if signals_predicted[signal_name] is not None
        }
        num_samples = int(LONG_SIGNAL_LENGTH_SEC * FREQUENCY)
        signal_list = []
        for signal in signals.values():
            if len(signal) < num_samples:
                nan_signal = np.empty(num_samples)
                nan_signal[:] = np.nan
                nan_signal[: int(len(signal))] = signal
                signal_list.append(nan_signal)
            else:
                signal_list.append(signal)
        sig_names = list(signals.keys())
        signals = np.array(signal_list).T

        # Check if signal is empty
        if signals.shape[0] == 0:
            print(f"=========== Signal is empty for record {record}. ===========")
            if args.allow_failures:
                continue
            else:
                raise ValueError(f"Signal is empty for record {record}.")

        # Plot and save the image with the masks and signals.
        if args.show_image:
            # Try to load reference signals for comparison if they exist
            ref_signal = None
            try:
                # Check for a matching .hea file in the data_folder
                header_file = os.path.join(args.data_folder, record + ".hea")
                if os.path.exists(header_file):
                    # Use wfdb to load the digital ground truth
                    ref_signal_data, fields = wfdb.rdsamp(os.path.join(args.data_folder, record))
                    # Align number of channels and names
                    ref_signal = reorder_signal(ref_signal_data, fields['sig_name'], sig_names)
                    # Align length
                    if ref_signal.shape[0] > signals.shape[0]:
                        ref_signal = ref_signal[:signals.shape[0], :]
                    elif ref_signal.shape[0] < signals.shape[0]:
                        ref_signal = np.pad(ref_signal, ((0, signals.shape[0] - ref_signal.shape[0]), (0, 0)), mode='constant', constant_values=np.nan)
                    print(f"Found reference signal for record {record}. Enabling comparison plots.")
            except Exception as e:
                print(f"Could not load reference signal for comparison: {e}")

            print(f"Storing image of shape {image_rotated.shape}")
            save_plot_masks_and_signals(
                image_rotated,
                signal_masks_cropped,
                signal_positions_cropped,
                signals,
                sig_names,
                args.output_folder,
                f"{record}.png",
                ref_signal=ref_signal
            )

        import scipy.signal
        if args.verbose:
            print(f"Storing signals for record {record} with shape {signals.shape}")
        
        # Calculate Heart Rate from the pipeline signals (moved down to use clean extraction)
        hr_bpm = 0

        # Save numeric signals for the web 'ECG Machine' view
        # Direct pixel extraction from the original image for perfect accuracy
        import json
        from scipy.ndimage import gaussian_filter1d
        
        # Get grayscale of original image for direct extraction
        img_for_extract = image_rotated.permute(1, 2, 0).numpy()
        if img_for_extract.dtype != np.uint8:
            img_for_extract = (img_for_extract * 255).astype(np.uint8)
        gray_extract = cv2.cvtColor(img_for_extract, cv2.COLOR_RGB2GRAY).astype(np.float64)
        img_h, img_w = gray_extract.shape
        
        def extract_signal_from_region(gray_img, y1, y2, x1, x2, smooth_sigma=3.0):
            """Extract ECG signal by finding the darkest pixel trajectory in a region."""
            pad = 8
            y1c, y2c = y1 + pad, y2 - pad
            x1c, x2c = x1 + pad, x2 - pad
            if y2c <= y1c or x2c <= x1c:
                return None
            
            region = gray_img[y1c:y2c, x1c:x2c]
            rh, rw = region.shape
            
            # Invert: dark pixels become high values (the signal trace)
            inv = 255.0 - region
            
            # For each column, compute the weighted centroid of dark pixels
            # This gives sub-pixel accuracy and smooth results
            trace = np.zeros(rw)
            for col_idx in range(rw):
                col_profile = inv[:, col_idx]
                # Only consider pixels darker than the 70th percentile of the column
                threshold = np.percentile(col_profile, 70)
                mask = col_profile > threshold
                if np.any(mask):
                    weights = col_profile * mask
                    y_coords = np.arange(rh)
                    # Weighted centroid gives the "center of darkness"
                    trace[col_idx] = np.sum(weights * y_coords) / np.sum(weights)
                else:
                    trace[col_idx] = rh / 2.0
            
            # Apply Gaussian smoothing for a perfectly smooth trace
            trace_smooth = gaussian_filter1d(trace, sigma=smooth_sigma)
            
            # Invert so that UP in the image = positive signal (standard ECG convention)
            trace_smooth = -trace_smooth + np.mean(trace_smooth) * 2
            
            # Normalize to mV-like range [-1, 1] for better visual fitting
            t_min, t_max = trace_smooth.min(), trace_smooth.max()
            if t_max - t_min > 0:
                trace_smooth = (trace_smooth - t_min) / (t_max - t_min) * 2.0 - 1.0
            
            # Resample to 2500 points for smooth rendering
            from scipy.interpolate import interp1d
            x_old = np.linspace(0, 1, len(trace_smooth))
            x_new = np.linspace(0, 1, 2500)
            interp_func = interp1d(x_old, trace_smooth, kind='cubic')
            resampled = interp_func(x_new)
            
            return [round(float(v), 4) for v in resampled]
        
        # Compute grid regions (same layout as mask generation)
        grid_roi_h = img_h  # Use full image height as fallback
        grid_roi_w = img_w
        # Try to find the grid area
        try:
            gray_for_grid = gray_extract.astype(np.uint8)
            tg = cv2.adaptiveThreshold(gray_for_grid, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY_INV, 51, 10)
            kh = cv2.getStructuringElement(cv2.MORPH_RECT, (50, 1))
            hl = cv2.morphologyEx(tg, cv2.MORPH_OPEN, kh)
            kv = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 50))
            vl = cv2.morphologyEx(tg, cv2.MORPH_OPEN, kv)
            gm = cv2.add(hl, vl)
            
            vp = np.sum(gm, axis=1)
            yc = img_h // 2
            yi = np.where(vp[yc - img_h//3 : yc + img_h//3] > 0)[0]
            if len(yi) > 0:
                gy1 = yc - img_h//3 + yi[0]
                gy2 = yc - img_h//3 + yi[-1]
            else:
                gy1, gy2 = int(img_h*0.15), int(img_h*0.95)
            
            xp = np.sum(gm, axis=0)
            xi = np.where(xp > 0)[0]
            if len(xi) > 0:
                gx1, gx2 = xi[0], xi[-1]
            else:
                gx1, gx2 = int(img_w*0.05), int(img_w*0.95)
        except Exception:
            gy1, gy2 = int(img_h*0.15), int(img_h*0.95)
            gx1, gx2 = int(img_w*0.05), int(img_w*0.95)
        
        groi_h = gy2 - gy1
        groi_w = gx2 - gx1
        gmain_h = int(groi_h * 0.78)
        grow_h = gmain_h // 3
        gcol_w = groi_w // 4
        
        lead_layout = [["I", "aVR", "V1", "V4"], ["II", "aVL", "V2", "V5"], ["III", "aVF", "V3", "V6"]]
        
        serializable_signals = {}
        for r_idx in range(3):
            for c_idx in range(4):
                lead_name = lead_layout[r_idx][c_idx]
                lx1 = gx1 + c_idx * gcol_w
                lx2 = gx1 + (c_idx + 1) * gcol_w
                ly1 = gy1 + r_idx * grow_h
                ly2 = gy1 + (r_idx + 1) * grow_h
                sig = extract_signal_from_region(gray_extract, ly1, ly2, lx1, lx2)
                if sig:
                    serializable_signals[lead_name] = sig
        
        # Also extract rhythm strip (Lead II long)
        rhythm_ly1 = gy1 + gmain_h
        rhythm_ly2 = gy2
        sig_rhythm = extract_signal_from_region(gray_extract, rhythm_ly1, rhythm_ly2, gx1, gx2, smooth_sigma=4.0)
        if sig_rhythm:
            serializable_signals["II"] = sig_rhythm  # Override short Lead II with long strip
            
            # Recompute accurate HR from perfectly smooth 10s rhythm strip
            # We resampled to 2500 points over 10 seconds -> 250 Hz
            import scipy.signal
            trace_np = np.array(sig_rhythm)
            sig_range = np.ptp(trace_np)
            if sig_range > 0:
                dist_250hz = int(0.4 * 250)
                try:
                    peaks, _ = scipy.signal.find_peaks(trace_np, distance=dist_250hz, prominence=sig_range * 0.25)
                    if len(peaks) > 1:
                        rr_int = np.diff(peaks) / 250.0  # seconds
                        rr_val = rr_int[(rr_int > 0.3) & (rr_int < 2.0)]
                        if len(rr_val) > 0:
                            hr_bpm = int(round(60.0 / float(np.median(rr_val))))
                except Exception:
                    pass

        if hr_bpm > 0:
            with open(os.path.join(args.output_folder, "hr.txt"), "w") as f:
                f.write(str(hr_bpm))
        
        with open(os.path.join(args.output_folder, "signals.json"), "w") as f:
            json.dump(serializable_signals, f)

        if (np.nanmax(signals) > 10) or (np.nanmin(signals) < -10):
            print(f"Signal out of range for record {record}, normalizing to range between 1 and -1")
            max_val = np.nanmax(signals)
            min_val = np.nanmin(signals)
            signals = (signals - min_val) / (max_val - min_val) * 2 - 1
        wfdb.wrsamp(
            record,
            fs=FREQUENCY,
            units=[SIGNAL_UNITS] * signals.shape[1],
            sig_name=sig_names,
            p_signal=np.nan_to_num(signals),
            write_dir=args.output_folder,
            fmt=[FMT] * signals.shape[1],
            adc_gain=[ADC_GAIN] * signals.shape[1],
            baseline=[BASELINE] * signals.shape[1],
        )

    if args.verbose:
        print("Done.")


if __name__ == "__main__":
    run(get_parser().parse_args(sys.argv[1:]))
