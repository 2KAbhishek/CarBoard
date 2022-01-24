from tkinter import *
from tkinter.ttk import *
from tkinter.font import *
import math
import pyglet
import socket
import time


def fetch_data(the_socket, timeout=2):
    # Make socket non blocking
    the_socket.setblocking(False)

    # Total data partwise in a list
    total_data = []

    # Beginning time
    begin = time.time()
    while True:
        # If you got some data, then break after timeout
        if total_data and time.time() - begin > timeout:
            break
        # If you got no data at all, wait a little longer, twice the timeout
        elif time.time() - begin > timeout * 2:
            break

        # Receive something
        try:
            data = the_socket.recv(8192)
            if data:
                total_data.append(data)
                # Change the beginning time for measurement
                begin = time.time()
            else:
                # Sleep for sometime to indicate a gap
                time.sleep(0.1)
        except Exception as e:
            # print(e)
            pass

    # Join all parts in the list to make final bytes string
    return b''.join(total_data)


def update_data(indicators):
    # Create the message to receive RPM data
    RPMRequest = b'010C\r'
    client.sendall(RPMRequest)
    RPMData = fetch_data(client, 1)

    # Clean the data and convert it to string
    RPMData = RPMData.replace(RPMRequest, b'').replace(b' \r\r>', b'')
    RPMData = RPMData.decode('utf-8')

    RPMParts = RPMData.split(' ')
    if len(RPMParts) != 4 or RPMParts[0] != '41' or RPMParts[1] != '0C':
        print('Invalid RPM response')
    else:
        # Calculate RPM
        rpm = (256 * int(RPMParts[2], 16) + int(RPMParts[3], 16)) / 4

        update_indicator(
            round(rpm), indicators[0], indicators[1], indicators[2], 0, 8000, 4)

    # Create the message to receive speed data
    SpeedRequest = b'010D\r'

    client.sendall(SpeedRequest)
    SpeedData = fetch_data(client, 1)
    # Clean the data and convert it to string
    SpeedData = SpeedData.replace(SpeedRequest, b'').replace(b' \r\r>', b'')
    SpeedData = SpeedData.decode('utf-8')
    SpeedParts = SpeedData.split(' ')
    if len(SpeedParts) != 3 or SpeedParts[0] != '41' or SpeedParts[1] != '0D':
        print('Invalid response')
    else:
        # Calculate speed
        speed = int(RPMParts[2], 16)

        update_indicator(
            speed, indicators[0], indicators[3], indicators[4], 0, 280, 3)

    gui.after(500, update_data, indicators)


def update_indicator(value, cnvs, indicator_id, text_id, low_r, high_r, num_digits,
                     start_deg=225, end_deg=-45):
    # scale the angle according to the value
    deg_range = start_deg - end_deg
    val_range = high_r - low_r

    scaled_value = float(value - low_r)/float(val_range)
    scaled_angle = start_deg - (scaled_value * deg_range)

    # redraw the indicator line
    old_coords = cnvs.coords(indicator_id)

    indicator_length = math.sqrt(math.pow(old_coords[2] - old_coords[0], 2) + math.
                                 pow(old_coords[3] - old_coords[1], 2))

    new_coords = (old_coords[0], old_coords[1], old_coords[0] + indicator_length *
                  math.cos(math.radians(
                      scaled_angle)), old_coords[1] - indicator_length * math.sin(math.radians(scaled_angle))
                  )

    cnvs.coords(indicator_id, new_coords)
    # update the display text
    cnvs.itemconfig(text_id, text=str(value).rjust(num_digits, '0'))


def draw_gauge_lines(cnvs, coords, labels, secondary_lines=True, major_tick_length=25, minor_tick_length=10, width=2, start_deg=225, end_deg=-45):
    deg_range = start_deg - end_deg
    num_lines = len(labels)

    radius = (coords[2] - coords[0])/2
    center = coords[0] + radius, coords[1] + radius

    major_coords = []
    minor_coords = []

    # compute x, y coordinates of major and minor ticks
    for i in range(num_lines):
        angle = start_deg - i * deg_range/(num_lines - 1)
        x = center[0] + radius * math.cos(math.radians(angle))
        y = center[1] - radius * math.sin(math.radians(angle))
        major_coords.append((x, y, angle))

        if secondary_lines:
            angle = angle - deg_range/(2 * (num_lines - 1))
            x = center[0] + radius * math.cos(math.radians(angle))
            y = center[1] - radius * math.sin(math.radians(angle))
            minor_coords.append((x, y, angle))

    # remove last minor tick
    minor_coords.pop()
    # compute the maximum number of characters for padding
    max_num_chars = len(str(labels[len(labels) - 1]))

    # draw major ticks
    for i, tick in enumerate(major_coords):
        angle = 180 + tick[2]
        line_coords = (
            tick[0],
            tick[1],
            tick[0] + major_tick_length * math.cos(math.radians(angle)),
            tick[1] - major_tick_length * math.sin(math.radians(angle))
        )

        # pad the label text
        text = str(labels[i]).ljust(max_num_chars, ' ')

        text_size = Font(font=('Helvetica', 12, 'bold')).measure(text)

        text_x = line_coords[2] + (5 + text_size) * \
            math.cos(math.radians(angle))
        text_y = line_coords[3] - 15 * math.sin(math.radians(angle))

        cnvs.create_line(line_coords, width=width, fill='white')
        cnvs.create_text(text_x, text_y, font=(
            'Helvetica', 12, 'bold'), text=text, fill='white')

    # draw minor ticks
    for i, tick in enumerate(minor_coords):
        angle = 180 + tick[2]
        line_coords = (
            tick[0],
            tick[1],
            tick[0] + minor_tick_length * math.cos(math.radians(angle)),
            tick[1] - minor_tick_length * math.sin(math.radians(angle))
        )

        cnvs.create_line(line_coords, width=width, fill='white')

    # draw gauge indicator
    indicator_coords = (
        center[0],
        center[1],
        center[0]+(radius-major_tick_length-10) *
        math.cos(math.radians(start_deg)),
        center[1]-(radius-major_tick_length-10) *
        math.sin(math.radians(start_deg))
    )

    indicator_line_id = cnvs.create_line(
        indicator_coords, width=2 * width, fill='#da0433')

    # return indicator id
    return indicator_line_id


def draw_main_gauges(app):
    # create a canvas element
    cnvs = Canvas(app)
    # set the background color
    cnvs.configure(background='#131318')

    # define the gauge radius and gap
    radius = 180
    gap = 80

    # rpm gauge coordinates
    rpm_coords = (
        window_width/2 - 2 * radius - gap/2,
        window_height/2 - radius,
        window_width/2 - gap/2,
        window_height/2 + radius
    )

    # draw rpm gauge circle
    rpm_gauge = cnvs.create_oval(rpm_coords, width=3, outline='#dedede')

    # define the rpm labels and draw the ticks
    rpm_labels = range(9)
    rpm_indicator = draw_gauge_lines(cnvs, rpm_coords, rpm_labels)

    # display rpm text
    rpm_text = 'x1000 rpm'
    text_size = Font(font=('Helvetica', 12, 'bold')).measure(rpm_text)

    rpm_text_coords = (
        rpm_coords[0] + radius,
        rpm_coords[1] + 100
    )

    cnvs.create_text(
        rpm_text_coords,
        font=('Helvetica', 12, 'bold'),
        text=rpm_text,
        fill='white'
    )
    # draw the rpm display
    text_size = Font(font=('DSEG14 Classic', 24, 'bold')).measure('0000')

    display_background_coords = (
        rpm_coords[0] + radius - text_size/2 - 10,
        rpm_coords[1] + 300 - 30,
        rpm_coords[0] + radius + text_size/2 + 8,
        rpm_coords[1] + 300 + 26,
    )

    rpm_display_coords = (
        display_background_coords[0] + text_size/2 + 10,
        display_background_coords[1] + 26
    )

    # draw the display background and 7 segment text
    cnvs.create_rectangle(display_background_coords, fill='#da0433')

    rpm_text = cnvs.create_text(
        rpm_display_coords,
        font=('DSEG14 Classic', 24, 'bold'),
        text='0000',
        fill='white'
    )

    # speed gauge coordinates
    speed_coords = (
        window_width/2 + gap/2,
        window_height/2 - radius,
        window_width/2 + 2 * radius + gap/2,
        window_height/2 + radius
    )

    # draw speed gauge circle
    speed_gauge = cnvs.create_oval(speed_coords, width=3, outline='#dedede')

    # define the speed labels and draw the ticks
    speed_labels = range(0, 300, 20)
    speed_indicator = draw_gauge_lines(cnvs, speed_coords, speed_labels)

    # display speed text
    speed_text = 'km/h'
    text_size = Font(font=('Helvetica', 12, 'bold')).measure(speed_text)
    speed_text_coords = (
        speed_coords[0] + radius,
        speed_coords[1] + 100
    )
    cnvs.create_text(
        speed_text_coords,
        font=('Helvetica', 12, 'bold'),
        text=speed_text,
        fill='white'
    )

    # draw the speed display
    text_size = Font(font=('DSEG14 Classic', 24, 'bold')).measure('000')

    display_background_coords = (
        speed_coords[0] + radius - text_size/2 - 10,
        speed_coords[1] + 300 - 30,
        speed_coords[0] + radius + text_size/2 + 8,
        speed_coords[1] + 300 + 26,
    )

    speed_display_coords = (
        display_background_coords[0] + text_size/2 + 10,
        display_background_coords[1] + 26
    )

    # draw the display background and 7 segment text
    cnvs.create_rectangle(display_background_coords, fill='#da0433')

    speed_text = cnvs.create_text(
        speed_display_coords,
        font=('DSEG14 Classic', 24, 'bold'),
        text='000',
        fill='white'
    )

    # Pack the canvas to fill the main window
    cnvs.pack(fill=BOTH, expand=1)

    # return the canvas and dynamic indicators ids
    return cnvs, rpm_indicator, rpm_text, speed_indicator, speed_text


def close_gui():
    # destroy the window
    gui.destroy()
    # close the socket connection
    client.close()


if __name__ == '__main__':
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print('Socket Created')
    CAR_IP = '127.0.0.1'
    CAR_PORT = 35000

    # Connect the socket object to the ELM327 server
    client.connect((CAR_IP, CAR_PORT))
    print('Socket Connected to {}:{}'.format(CAR_IP, CAR_PORT))
    # define starting parameters
    speed = 0
    rpm = 0

    # import font
    pyglet.font.add_file('fonts/DSEG14Classic-Regular.ttf')
    pyglet.font.add_file('fonts/DSEG14Classic-Bold.ttf')

    # set window size
    window_width = 1280
    window_height = 720

    # create the window
    gui = Tk()
    gui.title('Dashboard')
    # get the screen dimension
    screen_width = gui.winfo_screenwidth()
    screen_height = gui.winfo_screenheight()

    # find the center point
    center_x = int(screen_width/2 - window_width / 2)
    center_y = int(screen_height/2 - window_height / 2)
    # Sets the geometry and position of window on the screen
    gui.geometry('{}x{}+{}+{}'.format(window_width,
                                      window_height, center_x, center_y))
    gui.resizable(False, False)
    # Close socket connection on window close
    gui.protocol('WM_DELETE_WINDOW', close_gui)

    # create graphics elements
    indicators = draw_main_gauges(gui)
    gui.after(1000, update_data, indicators)
    gui.mainloop()
