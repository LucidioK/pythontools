#!/usr/bin/env python3
import numpy as np
import cv2
import sys

if len(sys.argv) != 8:
    print('image_polygons.py image_file_path min_threshold max_threshold min_area min_points blur_size gamma')
    print('Example (this one works)')
    print('image_polygons.py /Users/lucidiok/Pictures/Bones/13_26.jpeg 190 255 40 7 2 .5')
    exit(1)

def adjust_gamma(image, gamma=1.0):
	invGamma    = 1.0 / gamma
	table       = np.array([((i / 255.0) ** invGamma) * 255
		for i in np.arange(0, 256)]).astype("uint8")
	return cv2.LUT(image, table)

def find_contours(file_path:str, min_threshold: int, max_threshold: int, min_area:int, min_points:int, blur_size:int, gamma:float = 1.0) -> np.ndarray:
    img2        = cv2.imread(file_path, cv2.IMREAD_COLOR)
    img         = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)
    img         = cv2.blur(img,ksize = (blur_size, blur_size))
    img         = adjust_gamma(img, gamma)
    _,threshold = cv2.threshold(img, min_threshold, max_threshold, cv2.THRESH_BINARY)
    contours,_  = cv2.findContours(threshold, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_TC89_KCOS)
    contours    = [contour for contour in contours if cv2.contourArea(contour) >= min_area and len(contour) >= min_points]
    colors      = [(0, 0, 255),(255, 0, 0),(0, 255, 0),(255, 0, 255),(255, 255, 0),(0, 255, 255),(0, 0, 185),(185, 0, 0),(0, 185, 0),(185, 0, 185),(185, 185, 0),(0, 185, 185),]
    count       = 0
    for contour in contours :
        approx  = cv2.approxPolyDP(contour, 0.001 * cv2.arcLength(contour, True), True)
        img2    = cv2.drawContours(img2, [approx], -1, colors[count % len(colors)], 2)
        count  += 1
    cv2.line(img2, [10,10], [10,20], (255,255,255), 2)
    cv2.line(img2, [10,20], [15,15], (255,255,  0), 2)
    return img2

file_path     = sys.argv[1]
min_threshold = int(sys.argv[2])
max_threshold = int(sys.argv[3])
min_area      = int(sys.argv[4])
min_points    = int(sys.argv[5])
blur_size     = int(sys.argv[6])
gamma         = float(sys.argv[7])

img_no_edge = find_contours(file_path, min_threshold, max_threshold, min_area, min_points, blur_size, gamma)
cv2.imshow('Final Contoured without edge', img_no_edge) 

print('Press any key to close the image.')
cv2.waitKey(0)
cv2.destroyAllWindows()
