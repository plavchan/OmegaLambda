from ..main.common.util import filereader_utils
import statistics
import matplotlib.pyplot as plt
import numpy as np
import os


def focus_test():
    last = None
    fwhm = None
    i = 0
    last_fwhm = None
    fwhm_values = []
    initial_position = 5916
    current_position = initial_position
    focus_positions = []
    while i < 10:
        fwhm = filereader_utils.radial_average(
            r'H:\Observatory Files\Observing Sessions\2020_Data\20200714\TOI_2022-01_120s_r-{0:04d}.fits'.format(i+30),
            20000)
        if abs(current_position - initial_position) >= 100:
            print('Focuser has moved more than 100 steps')
            break
        if not fwhm:
            print('No fwhm could be calculated...trying again')
            continue
        if i == 0:
            # First cycle
            current_position -= 20
            last = "in"

        elif abs(fwhm - last_fwhm) <= 0.5:
            # Focus noise control -- If less than 0.5 pixels different (about 0.175"), it will keep moving in
            # that direction and check again vs. the previous last_fwhm
            if last == "in":
                current_position -= 10
            elif last == "out":
                current_position += 10
            i += 1
            fwhm_values.append(fwhm)
            focus_positions.append(current_position)
            continue
        elif fwhm <= last_fwhm:
            # Better FWHM -- Keep going
            if last == "in":
                current_position -= 10
            elif last == "out":
                current_position += 10
        elif fwhm > last_fwhm:
            # Worse FWHM -- Switch directions
            if last == "in":
                current_position += 10
                last = "out"
            elif last == "out":
                current_position -= 10
                last = "in"
        last_fwhm = fwhm
        fwhm_values.append(fwhm)
        focus_positions.append(current_position)
        i += 1
        print('Fwhm = {}; position = {}'.format(fwhm, current_position))

    data = sorted(zip(focus_positions, fwhm_values))
    x = [_[0] for _ in data]
    y = [_[1] for _ in data]
    med = statistics.median(x)
    fit = np.polyfit(x, y, 2)
    xfit = np.linspace(med - 50, med + 50, 100)
    yfit = fit[0] * (xfit ** 2) + fit[1] * xfit + fit[2]
    fig, ax = plt.subplots()
    ax.plot(x, y, 'bo', label='Raw data')
    ax.plot(xfit, yfit, 'r-', label='Parabolic fit')
    ax.legend()
    ax.set_xlabel('Focus Positions (units)')
    ax.set_ylabel('FWHM value (pixels)')
    ax.set_title('Focus Position Graph')
    ax.grid()
    plt.savefig(os.path.join(r'C:/Users/GMU Observtory1/-omegalambda/test/FocusPlot.png'))

    minindex = np.where(yfit == min(yfit))
    if (minindex == np.where(yfit == yfit[0])) or (minindex == np.where(yfit == yfit[-1])):
        print('Parabolic fit has failed and fit an incorrect parabola.  Cannot calculate minimum focus.')
        return
    minfocus = np.round(xfit[minindex])
    print('Autofocus achieved a FWHM of {} pixels!'.format(fwhm))
    print('The theoretical minimum focus was calculated to be at position {}'.format(minfocus))
    if abs(initial_position - minfocus) <= 100:
        current_position = minfocus
        print('Final focus position = {}'.format(current_position))
    else:
        print('Calculated minimum focus is out of range of the focuser movement restrictions. '
              'This is probably due to an error in the calculations.')
    return

if __name__ == '__main__':
    focus_test()