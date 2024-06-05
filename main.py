import pyautogui
import pygame
import numpy as np
import matplotlib.pyplot as plt

pygame.mixer.init()

sound = pygame.mixer.Sound('alarm.wav')

monitor_area = (0, 650, 200, 150)

screenshot1 = pyautogui.screenshot(region=monitor_area)

fig1, ax1 = plt.subplots()

image1 = ax1.imshow(screenshot1)

fig2, ax2 = plt.subplots()

while True:
    screenshot2 = pyautogui.screenshot(region=monitor_area)
    image1.set_data(screenshot2)
    plt.pause(3)
    image2 = ax2.imshow(screenshot2)
    fig2.canvas.draw()
    if not np.array_equal(np.array(screenshot1), np.array(screenshot2)):
        print('Change detected!')
        while True:
            sound.play()
            pygame.time.wait(28000)
    else:
        screenshot1 = screenshot2
