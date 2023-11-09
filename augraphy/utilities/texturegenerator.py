import cv2
import numba as nb
import numpy as np
from numba import config
from numba import jit
import random
from sklearn.datasets import make_blobs

from augraphy.augmentations.lib import enhance_contrast

class TextureGenerator:
    """Core object to generate mask of texture in paper.
   
    1. "normal"  : Texture generated by multiple additions of normal distribution noise.
    2. "strange" : Texture generated by an algorithm called "strange pattern".
    3. "rough_stains": A rough stains similar texture generated by using FFT. 
    4. "fine_stains": A fine stains similar texture generated by using FFT. 
    5. "granular": A light granular texture generated by using FFT.
    6. "curvy_edge": Texture with distinct curvy effect on the images edges. Generated by using FFT.
    7. "broken_edge": Texture with broken images edges effect. Generated by using FFT.
   
    :param numba_jit: The flag to enable numba jit to speed up the processing.
    :type numba_jit: int, optional
    """

    def __init__(self,  numba_jit=1):
        self.numba_jit = numba_jit
        config.DISABLE_JIT = bool(1 - numba_jit)

    # Adapted from this link:
    # # https://stackoverflow.com/questions/51646185/how-to-generate-a-paper-like-background-with-opencv
    def generate_normal_texture(self, xsize, ysize, channel, value=255, sigma=1, turbulence=2):
        """Generate random texture through multiple iterations of normal distribution noise addition.
    
        :param xsize: The width of the generated noise.
        :type xsize: int
        :param ysize: The height of the generated noise.
        :type ysize: int
        :param channel: The number of channel in the generated noise.
        :type channel: int
        :param value: The initial value of the generated noise.
        :type value: int
        :param sigma: The bounds of noise fluctuations.
        :type sigma: float
        :param turbulence: The value to define how quickly big patterns will be replaced with the small ones.
        :type turbulence: int
    
        """
        image_output = np.full((ysize, xsize), fill_value=value, dtype="float")
        ratio = min(xsize, ysize)
        while ratio != 1:
            new_ysize = int(ysize / ratio)
            new_xsize = int(xsize / ratio)
            result = np.random.normal(0, sigma, (new_xsize, new_ysize, channel))
            if ratio != 1:
                result = cv2.resize(result, dsize=(xsize, ysize), interpolation=cv2.INTER_LINEAR)
            image_output += result
            ratio = (ratio // turbulence) or 1
        image_output = np.clip(image_output, 0, 255)
    
        new_min = 32
        new_max = 255
        image_output = ((image_output - np.min(image_output)) / (np.max(image_output) - np.min(image_output))) * (
            new_max - new_min
        ) + new_min
    
        # convert to uint8
        image_output = np.uint8(image_output)
    
        # conver to color image
        if channel == 3:
            image_output = cv2.cvtColor(image_output, cv2.COLOR_GRAY2BGR)
    
        return image_output
    
    
    # adapted from this repository:
    # https://github.com/NewYaroslav/strange_pattern
    @staticmethod
    @jit(nopython=True, cache=True, parallel=True)
    def generate_strange_texture(oxsize, oysize):
        """Generate a random strange texture.
    
        :param oxsize: The width of the output texture image.
        :type oxsize: int
        :param oysize: The height of the output texture image.
        :type oysize: int
        """
    
        background_value = random.uniform(0.04, 0.11)
    
        # initialize random parameter
        t_random = random.uniform(0, 100)
        m_random = [random.uniform(0, 100), random.uniform(0, 100)]
    
        # initialize output
        image_strange_texture = np.zeros((oysize, oxsize, 3))
    
        # calculate color
        for y in nb.prange(oysize):
            for x in nb.prange(oxsize):
    
                # initial value
                value = int(x + t_random * 80.0 + m_random[0] * 10.0) ^ int(y + t_random * 80.0 + m_random[1] * 10.0)
    
                # update pixel value
                color = 1.0
                if value <= 1:
                    color = background_value
                if value % 2 == 0 and value > 2:
                    color = background_value
                for i in range(3, int(np.floor(np.sqrt(float(value)))), random.randint(1, 10)):
                    if value % i == 0:
                        color = background_value
    
                # generate random color
                new_color = [
                    color / random.uniform(0.01, 3),
                    color / random.uniform(0.01, 3),
                    color / random.uniform(0.01, 3),
                ]
    
                # update color
                image_strange_texture[y, x] = new_color
    
        # rotate texture randomly
        image_strange_texture = np.rot90(image_strange_texture, random.randint(0, 3))

        return image_strange_texture
    

    def generate_broken_edge_texture(self, oxsize, oysize):
        """Generate a mask of broken edges based texture.
    
        :param oxsize: The width of the output mask.
        :type oxsize: int
        :param oysize: The height of the output mask.
        :type oysize: int
        """
    
        iysize, ixsize = 400, 400
    
        # mask of noise
        image_noise = np.full((iysize, ixsize), fill_value=255, dtype="uint8")
    
        # image center
        center_xs = [0, int(ixsize / 2), ixsize, int(ixsize / 2)]
        center_ys = [int(iysize / 2), 0, int(iysize / 2), iysize]
    
        noise_value = [128, 255]
        n_clusters = [300, 500]
        n_samples = [1080, 1280]
        stds = [int(ixsize / 4), int(iysize / 4)]
    
        n_samples = [
            random.randint(n_samples[0], n_samples[1]) for i in range(random.randint(n_clusters[0], n_clusters[1]))
        ]
        std = random.randint(stds[0], stds[1])
    
        generated_points_x = np.array([[0]], dtype=("float"))
        generated_points_y = np.array([[0]], dtype=("float"))
    
        for center_x, center_y in zip(center_xs, center_ys):
    
            # generate clusters of noises
            cgenerated_points_x, _ = make_blobs(
                n_samples=n_samples,
                center_box=(center_x, center_x),
                cluster_std=std,
                n_features=1,
            )
    
            # generate clusters of noises
            cgenerated_points_y, _ = make_blobs(
                n_samples=n_samples,
                center_box=(center_y, center_y),
                cluster_std=std,
                n_features=1,
            )
    
            generated_points_x = np.concatenate((generated_points_x, cgenerated_points_x), axis=0)
            generated_points_y = np.concatenate((generated_points_y, cgenerated_points_y), axis=0)
    
        # generate x and y points of noise
        generated_points_x = generated_points_x.astype("int")
        generated_points_y = generated_points_y.astype("int")
    
        # remove invalid points
        ind_delete_x1 = np.where(generated_points_x < 2)
        ind_delete_x2 = np.where(generated_points_x >= ixsize - 2)
        ind_delete_y1 = np.where(generated_points_y < 2)
        ind_delete_y2 = np.where(generated_points_y >= iysize - 2)
    
        ind_delete = np.concatenate(
            (ind_delete_x1, ind_delete_x2, ind_delete_y1, ind_delete_y2),
            axis=1,
        )
        generated_points_x = np.delete(generated_points_x, ind_delete, axis=0)
        generated_points_y = np.delete(generated_points_y, ind_delete, axis=0)
    
        # update noise value
        image_random = np.random.random((iysize, ixsize))
        image_random[image_random < noise_value[0] / 255] = 0
        image_random[image_random > noise_value[1] / 255] = 0
        image_random = (image_random * 255).astype("uint8")
    
        # update points with random value
        image_noise[generated_points_y, generated_points_x] = image_random[generated_points_y, generated_points_x]
    
        # apply blur
        image_noise = cv2.GaussianBlur(image_noise, (random.choice([7, 9, 11, 13]), random.choice([7, 9, 11, 13])), 0)
    
        # create edge texture
        image_edge_texture = image_noise + image_noise
    
        # resize to expected size
        image_edge_texture = cv2.resize(image_edge_texture, (oxsize, oysize), interpolation=cv2.INTER_LINEAR)
    
        return image_edge_texture


    def generate_rough_stains_texture(self, oxsize, oysize):
        """Generate a rough stains similar texture using FFT.
    
        :param oxsize: The width of the output texture image.
        :type oxsize: int
        :param oysize: The height of the output texture image.
        :type oysize: int
        """
    
        # fixed internal resolution
        ysize, xsize = 200, 200
        wave_grid_output = self.generate_FFT_grid(xsize, ysize, f_iterations=(3,5), g_iterations=(2,4), rresolutions=(0.95, 0.95),  rA=(5,15), rf=(0.01, 0.03), rp=(0, 2 * np.pi), rkx=(-1, 1), rky=(-1, 1))
        
        # blur to smoothen texture
        wave_grid_output = cv2.GaussianBlur(wave_grid_output, (3, 3), 0)
    
        # remove low frequency area
        wave_grid_output = self.remove_frequency(wave_grid_output, random.randint(25, 35))
    
        # median filter to smoothen texture
        wave_grid_output = cv2.medianBlur(wave_grid_output, 5)
    
        # resize to output size
        wave_grid_output = cv2.resize(wave_grid_output, (oxsize, oysize), interpolation=cv2.INTER_LINEAR)
    
        return wave_grid_output
    
    
    def generate_granular_texture(self, oxsize, oysize):
        """Generate random granular texture using FFT.
    
        :param oxsize: The width of the output texture image.
        :type oxsize: int
        :param oysize: The height of the output texture image.
        :type oysize: int
        """
    
        # fixed internal resolution
        ysize, xsize = 500, 500
        wave_grid_output = self.generate_FFT_grid(xsize, ysize, f_iterations=(1,1), g_iterations=(1,1), rresolutions=(0.95, 0.95),  rA=(5,15), rf=(0.01, 0.02), rp=(0, 2 * np.pi), rkx=(-1, 1), rky=(-1, 1))

        # blur to smoothen texture
        wave_grid_output = cv2.GaussianBlur(wave_grid_output, (3, 3), 0)
    
        # remove frequency > 10
        frequency = 10
        wave_grid_output = self.remove_frequency(wave_grid_output, frequency=frequency)
    
        # remove border textures
        offset = 50
        wave_grid_output = wave_grid_output[offset:-offset, offset:-offset]
    
        # rescale
        wave_grid_output = (wave_grid_output - wave_grid_output.min()) / (wave_grid_output.max() - wave_grid_output.min())
        wave_grid_output = 255 - np.uint8(wave_grid_output * 255)
    
        # remove frequency > 100
        frequency = 100
        wave_grid_output = self.remove_frequency(wave_grid_output, frequency)
    
        # rescale again
        wave_grid_output = (wave_grid_output - wave_grid_output.min()) / (wave_grid_output.max() - wave_grid_output.min())
        wave_grid_output = np.uint8(wave_grid_output * 255)
    
        # resize to output size
        wave_grid_output = cv2.resize(wave_grid_output, (oxsize, oysize), interpolation=cv2.INTER_LINEAR)
    
        return wave_grid_output
    
    
    def generate_curvy_edge_texture(self, oxsize, oysize):
        """Generate a masked of curves based edge texture using FFT.
    
        :param oxsize: The width of the output texture image.
        :type oxsize: int
        :param oysize: The height of the output texture image.
        :type oysize: int
        """
    
        # fixed internal resolution
        ysize, xsize = 500, 500
        wave_grid_output = self.generate_FFT_grid(xsize, ysize, f_iterations=(1,1), g_iterations=(1,1), rresolutions=(0.95, 0.95),  rA=(5,15), rf=(0.05, 0.1), rp=(0, 2 * np.pi), rkx=(-1, 1), rky=(-1, 1))
    
        # blur to smoothen texture
        wave_grid_output = cv2.GaussianBlur(wave_grid_output, (3, 3), 0)
    
        # remove frequency > 100
        frequency = 100
        wave_grid_output = self.remove_frequency(wave_grid_output, frequency=frequency)
    
        # rescale
        wave_grid_output = (wave_grid_output - wave_grid_output.min()) / (wave_grid_output.max() - wave_grid_output.min())
        wave_grid_output = np.uint8(wave_grid_output * 255)
    
        # blur to smoothen trexture
        wave_grid_output = cv2.GaussianBlur(wave_grid_output, (9, 9), 0)
    
        # resize to output size
        wave_grid_output = cv2.resize(wave_grid_output, (oxsize, oysize), interpolation=cv2.INTER_LINEAR)
    
        return wave_grid_output
    
    
    def generate_fine_stains_texture(self, oxsize, oysize):
        """Generate a fine stains similar texture using combination of normal distribution noise and FFT.
    
        :param oxsize: The width of the output texture image.
        :type oxsize: int
        :param oysize: The height of the output texture image.
        :type oysize: int
        """
    
        # fixed internal resolution
        ysize, xsize = 500, 500
        wave_grid_output = self.generate_FFT_grid(xsize, ysize, f_iterations=(1,1), g_iterations=(3,5), rresolutions=(0.95, 0.95), rA=(5,15), rf=(0.01, 0.02), rp=(0, 2 * np.pi), rkx=(-1, 1), rky=(-1, 1))
    
        wave_grid_output += self.generate_normal_texture(ysize, xsize, 1, value=255, sigma=1, turbulence=2)
    
        # blur to smoothen texture
        wave_grid_output = cv2.GaussianBlur(wave_grid_output, (3, 3), 0)
    
        # remove frequency > 10
        frequency = 10
        wave_grid_output = self.remove_frequency(wave_grid_output, frequency=frequency)
    
        # remove border textures
        offset = 50
        wave_grid_output = wave_grid_output[offset:-offset, offset:-offset]
    
        # rescale
        wave_grid_output = (wave_grid_output - wave_grid_output.min()) / (wave_grid_output.max() - wave_grid_output.min())
        wave_grid_output = 255 - np.uint8(wave_grid_output * 255)
    
        # remove frequency > 100
        frequency = 100
        wave_grid_output = self.remove_frequency(wave_grid_output, frequency)
    
        # rescale again
        wave_grid_output = (wave_grid_output - wave_grid_output.min()) / (wave_grid_output.max() - wave_grid_output.min())
        wave_grid_output = np.uint8(wave_grid_output * 255)
    
        # blur to smoothen texture
        wave_grid_output = cv2.GaussianBlur(wave_grid_output, (3, 3), 0)
    
        # resize to output size
        wave_grid_output = cv2.resize(wave_grid_output, (oxsize, oysize), interpolation=cv2.INTER_LINEAR)
    
        return wave_grid_output
    
    
    
    def generate_FFT_grid(self, xsize, ysize, f_iterations, g_iterations, rresolutions, rA, rf, rp, rkx, rky):
        """Generate random wave grid, process it in FFT and convert it back into spatial domain.
    
        :param xsize: The width of the output image.
        :type xsize: int
        :param ysize: The height of the output image.
        :type ysize: int
        :param f_iterations: Tuple of ints in determining the number of iterations in adding FFT converted wave grid.
        :type f_iterations: tuple
        :param g_iterations: Tuple of ints in determining the number of iterations in summing grid waves.
        :type g_iterations: tuple
        :param rresolutions: Tuple of floats in determing the resolution of grid image.
        :type rresolutions: tuple
        :param rA: Tuple of ints in determining the amplitude of waves.
        :type rA: tuple
        :param rf: Tuple of floats in determining the frequency of waves.
        :type rf tuple
        :param rp: Tuple of floats in determining the phase of waves.
        :type rp tuple
        :param rkx: Tuple of floats in determining the x-component of wave vector.
        :type rkx tuple
        :param rky: Tuple of floats in determining the y-component of wave vector.
        :type rky tuple
        
        """

        wave_grid_output = np.zeros((ysize, xsize), dtype="uint8")
    
        for i in range(random.randint(f_iterations[0],  f_iterations[1])):
            # fixed resolution of the wave image
            resolution = random.uniform(rresolutions[0], rresolutions[1])
    
            # Create a 2D grid of coordinates
            x_array = np.arange(-xsize / 2, xsize / 2) * resolution
            y_array = np.arange(-ysize / 2, ysize / 2) * resolution
            x_grid, y_grid = np.meshgrid(x_array, y_array)
    
            wave_grid_fft_shifted = np.zeros((ysize, xsize), dtype="complex")
            for i in range(random.randint(g_iterations[0], g_iterations[1])):
                # iterations for adding waves
                wave_grid = self.generate_wave_grid(x_grid, y_grid, xsize, ysize, iterations=(2,4), rA=rA, rf=rf, rp=rp, rkx=rkx, rky=rky)
    
                # Compute the FFT of the wave heights, shift the zero-frequency component to the center and then sum them
                wave_grid_fft_shifted += np.fft.fftshift(np.fft.fft2(wave_grid))
    
            # unshift the FFT component
            new_wave_grid = np.fft.ifft2(np.fft.ifftshift((wave_grid_fft_shifted)))
    
            # get the real part only
            new_wave_grid = np.real(new_wave_grid)
    
            # scale to 0 -1
            new_wave_grid = (new_wave_grid - new_wave_grid.min()) / (new_wave_grid.max() - new_wave_grid.min())
    
            # convert to uint8
            new_wave_grid = np.uint8(new_wave_grid * 255)
    
            # merge into output
            wave_grid_output += new_wave_grid
    
    
        return wave_grid_output

    
    def generate_wave_grid(self, xgrid, ygrid, xsize, ysize, iterations, rA, rf, rp, rkx, rky):
        """ Create grid of waves using heights of sine and cosine waves.
        
        :param xgrid: The x coordinates grid.
        :type xgrid: numpy array
        :param ygrid: The y coordinates grid.
        :type ygrid: numpy array
        :param xsize: The width of the output grid image.
        :type xsize: int
        :param ysize: The height of the output grid image.
        :type ysize: int
        :param iterations: The number of iterations in summing waves.
        :type iterations: tuple
        :param rA: Tuple of ints in determining the amplitude of waves.
        :type rA: tuple
        :param rf: Tuple of floats in determining the frequency of waves.
        :type rf tuple
        :param rp: Tuple of floats in determining the phase of waves.
        :type rp tuple
        :param rkx: Tuple of floats in determining the x-component of wave vector.
        :type rkx tuple
        :param rky: Tuple of floats in determining the y-component of wave vector.
        :type rky tuple
        """ 
        
        # iterations for adding waves
        current_iterations = random.randint(iterations[0], iterations[1])
        
        wave_grid = np.zeros((ysize, xsize), dtype="float")
        for i in range(current_iterations):

            # Calculate the wave height using a sine function
            A = np.random.uniform(rA[0], rA[1])  # Amplitude
            f = np.random.uniform(rf[0], rf[1])  # Frequency
            p = np.random.uniform(rp[0], rp[1])  # Phase
            kx = np.random.uniform(rkx[0], rkx[1])  # x-component of wave vector
            ky = np.random.uniform(rky[0], rky[1])  # y-component of wave vector
            h_sine = A * np.sin(2 * np.pi * (f * (kx * xgrid + ky * ygrid) - p))

            # Calculate the wave height using a cosine function
            A = np.random.uniform(rA[0], rA[1])  # Amplitude
            f = np.random.uniform(rf[0], rf[1])  # Frequency
            p = np.random.uniform(rp[0], rp[1])  # Phase
            kx = np.random.uniform(rkx[0], rkx[1])  # x-component of wave vector
            ky = np.random.uniform(rky[0], rky[1])  # y-component of wave vector
            h_cosine = A * np.cos(2 * np.pi * (f * (kx * xgrid + ky * ygrid) - p))

            # combine heights from sine and cosine
            wave_grid = h_sine + h_cosine
            
        return wave_grid

                    
    def remove_frequency(self, wave_grid_output, frequency):
        """Remove image area bigger than the input frequency by using FFT.
    
        :param wave_grid_output: The input image.
        :type wave_grid_output: numpy array
        :param frequency: The frequency threshold.
        :type frequency: int
        """
    
        ysize, xsize = wave_grid_output.shape[:2]
    
        cy, cx = ysize // 2, xsize // 2
        mask = np.ones((ysize, xsize), np.uint8)
    
        r = random.randint(frequency, frequency)
    
        # compute mask to remove low frequency area
        y, x = np.ogrid[:ysize, :xsize]
        mask_area = (x - cx) ** 2 + (y - cy) ** 2 <= r * r
        mask[mask_area] = 0
    
        # convert to fft and shift to zero-frequency
        wave_grid_output_fft = np.fft.fft2(wave_grid_output)
        wave_grid_output_fft_shifted = np.fft.fftshift(wave_grid_output_fft)
    
        # apply mask and inverse DFT
        wave_grid_output_fft_shifted *= mask
        wave_grid_output2_fft = np.fft.ifft2(np.fft.ifftshift(wave_grid_output_fft_shifted))
        wave_grid_output2 = np.abs(wave_grid_output2_fft)
    
        # normalize image back to 0 - 255
        wave_grid_output2 = (wave_grid_output2 - wave_grid_output2.min()) / (
            wave_grid_output2.max() - wave_grid_output2.min()
        )
        wave_grid_output = 255 - np.uint8(wave_grid_output2 * 255)
    
        return wave_grid_output
    
    
    
    def quilt_texture(self, image_texture, patch_size, patch_number_width, patch_number_height):
        """Generate new texture image by quilting patches of input image.
    
        :param image_texture: The input image texture.
        :type image_texture: numpy array
        :param patch_size: The size of each image patch.
        :type patch_size: int
        :param patch_number_width: The number of image patch in horizontal direction.
        :type patch_number_width: int
        :param patch_number_height: The number of image patch in vertical direction.
        :type patch_number_height: int
        """
    
        overlap = patch_size // 5
    
        # size of output
        ysize = (patch_number_height * patch_size) - (patch_number_height - 1) * overlap
        xsize = (patch_number_width * patch_size) - (patch_number_width - 1) * overlap
    
        # convert from gray to bgr
        is_gray = 0
        if len(image_texture.shape) < 3:
            is_gray = 1
            image_texture = cv2.cvtColor(image_texture, cv2.COLOR_GRAY2BGR)
    
        # output
        image_quilt = np.zeros((ysize, xsize, image_texture.shape[2]), dtype="uint8")
    
        # size of image texture
        ysize, xsize = image_texture.shape[:2]
    
        # hsv channel of texture
        image_hsv = cv2.cvtColor(image_texture, cv2.COLOR_BGR2HSV)
    
        # get a reference patch's hue, saturation and value
    
        n = 0
        while n < 10:
            y = np.random.randint(ysize - patch_size)
            x = np.random.randint(xsize - patch_size)
            # to prevent black or white blank image
            if (
                np.mean(image_hsv[y : y + patch_size, x : x + patch_size, 2]) < 245
                and np.mean(image_hsv[y : y + patch_size, x : x + patch_size, 2]) > 10
            ):
                break
            n += 1
    
        h_reference = np.mean(image_hsv[y : y + patch_size, x : x + patch_size, 0])
        s_reference = np.mean(image_hsv[y : y + patch_size, x : x + patch_size, 1])
        v_reference = np.mean(image_hsv[y : y + patch_size, x : x + patch_size, 2])
        offset = 10
        h_range = [h_reference - offset, h_reference + offset]
        s_range = [s_reference - offset, s_reference + offset]
        v_range = [v_reference - offset, v_reference + offset]
    
        # generate and apply random patch
        for i in range(patch_number_height):
            for j in range(patch_number_width):
                y = i * (patch_size - overlap)
                x = j * (patch_size - overlap)
                image_patch = self.get_random_patch(
                    image_texture,
                    image_hsv,
                    patch_size,
                    ysize,
                    xsize,
                    h_range,
                    s_range,
                    v_range,
                )
                image_quilt[y : y + patch_size, x : x + patch_size] = image_patch
    
        # smoothing
        image_quilt = cv2.medianBlur(image_quilt, ksize=11)
    
        # enhance contrast of texture
        image_quilt = enhance_contrast(image_quilt)
    
        # image follows input texture color channel
        if is_gray:
            image_quilt = cv2.cvtColor(image_quilt, cv2.COLOR_BGR2GRAY)
    
        return image_quilt
    
    
    def get_random_patch(self, image_texture, image_hsv, patch_size, ysize, xsize, h_range, s_range, v_range):
        """Get patch of image from texture based on input hue, saturation and value range.
    
        :param image_texture: The input image texture.
        :type image_texture: numpy array
        :param image_hsv: The input image texture in HSV channel.
        :type image_hsv: numpy array
        :param patch_size: The size of each image patch.
        :type patch_size: int
        :param y_size: The height of image texture.
        :type y_size: int
        :param x_size: The width of image texture.
        :type x_size: int
        :param h_range: The range of reference hue values.
        :type h_range: tuple
        :param s_range: The range of reference saturation values.
        :type s_range: tuple
        :param v_range: The range of reference value values.
        :type v_range: tuple
        """
    
        n = 0
        y = np.random.randint(ysize - patch_size)
        x = np.random.randint(xsize - patch_size)
        image_patch = image_texture[y : y + patch_size, x : x + patch_size]
    
        # use a fixed number to prevent infinity loops
        while n < 10:
    
            y = np.random.randint(ysize - patch_size)
            x = np.random.randint(xsize - patch_size)
    
            # get mean of h, s and v channel of current patch
            h_mean = np.mean(image_hsv[y : y + patch_size, x : x + patch_size, 0])
            s_mean = np.mean(image_hsv[y : y + patch_size, x : x + patch_size, 1])
            v_mean = np.mean(image_hsv[y : y + patch_size, x : x + patch_size, 2])
    
            if (
                h_mean >= h_range[0]
                and h_mean < h_range[1]
                and s_mean >= s_range[0]
                and s_mean < s_range[1]
                and v_mean >= v_range[0]
                and v_mean < v_range[1]
            ):
    
                # get patch of image
                image_patch = image_texture[y : y + patch_size, x : x + patch_size]
    
                # apply gamma correction
                mid = np.mean(v_range) / 255
                gamma = np.log(mid * 255) / np.log(v_mean)
                image_patch = np.power(image_patch, gamma).clip(0, 255).astype(np.uint8)
                break
    
            n += 1
    
        return image_patch
    
    

    def __call__(
        self,
        texture_type = "random",
        texture_width = 1000,
        texture_height =1000,
        quilt_texture = "random",
        quilt_size = (25, 40),

    ):
        """Main function to generate random textures.
        
        :param texture_type: Types of image texture.
        :type texture_type: string (optional)
        :param texture_width: Width of image texture output.
        :type texture_width: int (optional)
        :param texture_height: height of image texture output.
        :type texture_height: int (optional)
        :param quilt_texture: Flag to enable or disable the quilting of generated texture.
        :type quilt_texture: int or string (optional)
        :param quilt_size: Tuple of ints in determining the size of texture patch in quilting process.
        :type quilt_size: tuple (optional)
        """

        # check for image texture generation
        if texture_type == "random":
            texture_type = random.choice(["normal","strange", "rough_stains", "fine_stains", "granular", "curvy_edge", "broken_edge"])

        if texture_type == "normal":
            image_texture = self.generate_normal_texture(texture_width, texture_height,1, sigma=random.randint(3,5), turbulence=random.randint(3,9))
        elif texture_type == "strange":
            image_texture = self.generate_strange_texture(texture_width, texture_height)
            image_texture = cv2.cvtColor(np.uint8(image_texture * 255), cv2.COLOR_BGR2GRAY)
            image_texture = cv2.resize(image_texture, (texture_width, texture_height), interpolation=cv2.INTER_LINEAR)
        elif texture_type == "rough_stains":
            image_texture = self.generate_rough_stains_texture(texture_width, texture_height)
        elif texture_type == "fine_stains":
            image_texture = self.generate_fine_stains_texture(texture_width, texture_height)
        elif texture_type == "granular":
            image_texture = self.generate_granular_texture(texture_width, texture_height)
        elif texture_type == "curvy_edge":
            image_texture = self.generate_curvy_edge_texture(texture_width, texture_height)
        else:
            image_texture = self.generate_broken_edge_texture(texture_width, texture_height)
            # get mask of edge texture
            _, image_texture_binary = cv2.threshold(image_texture, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            # compute contours
            contours, hierarchy = cv2.findContours(
                image_texture_binary,
                cv2.RETR_LIST,
                cv2.CHAIN_APPROX_NONE,
            )
            # initialize mask of  edge texture
            image_texture_mask = np.zeros_like(image_texture, dtype="uint8")
            # find largest inner contour as edge texture
            for contour in contours:
                x0, y0, cwidth, cheight = cv2.boundingRect(contour)
                area = cv2.contourArea(contour)
                if area > (texture_height * texture_width * 0.6) and cwidth != texture_width and cheight != texture_height:
                    image_texture_mask = cv2.drawContours(image_texture_mask, [contour], -1, (255), cv2.FILLED)
                    break
            # remove area outside edge texture
            image_texture[image_texture_mask <= 0] = 0

        # check for image quilting
        if quilt_texture == "random":
            quilt_texture = random.choice([0,1])
            
        if quilt_texture:
            patch_size = random.randint(quilt_size[0], quilt_size[1])
            patch_number_width = int(texture_width / patch_size)
            patch_number_height = int(texture_height / patch_size)
            image_texture = self.quilt_texture(image_texture, patch_size, patch_number_width, patch_number_height)
            # resize to output size
            image_texture = cv2.resize(image_texture, (texture_width, texture_height), interpolation=cv2.INTER_LINEAR)


        return image_texture
