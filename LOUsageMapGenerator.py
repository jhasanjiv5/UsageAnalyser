'''Start file and Output file generators'''
import time
import zipfile
import logging
import csv
import os
import cv2
import numpy as np
from googleUpload import upload_files
import Record
import config
from distanceCalc import calculate_and_map, get_serial
import socket

from checkInternetConnection import connect

def create_zip(name):
    """create zip file for the final output"""
    def filter(name): return '.zip' in name or '.DS_Store' in name
    try:
        with zipfile.ZipFile('{}.zip'.format(name), 'w', zipfile.ZIP_DEFLATED) as zip_obj:
            for folder_name, subfolders, filenames in os.walk(config.OUTPUT_PATH):
                for filename in filenames:
                    if filter(filename):
                        continue
                    file_path = os.path.join(folder_name, filename)
                    zip_obj.write(file_path)
                    if (lambda name: '.log' not in name)(file_path):
                        os.remove(file_path)
    except Exception as e:
        print(e)
        logging.debug(e)

def adapt_blur(raw_image):
    """Check blur level of the raw image and adapt the additional internal level depending on blur level of the raw image"""
    BLUR_LEVEL=cv2.Laplacian(raw_image, cv2.CV_64F).var()
    #print(BLUR_LEVEL)
    try:
        if BLUR_LEVEL > 15:
            config.BLURR_SIZE = (3,3)
        elif (BLUR_LEVEL > 9) and (BLUR_LEVEL < 15):
            config.BLURR_SIZE = (1,1)
        elif BLUR_LEVEL < 9:
            config.BLURR_SIZE = (5,5)
    except Exception as e:
            print(e)
            raise Exception(e)
    #print(config.BLURR_SIZE)
    
def generate_map():
    """ generates scatter map and overlays on the empty room image for better analysis by the users 
     outputs found ROI coordinates and schedules the camera for reducing the battery life conservation """
    capture1 = cv2.VideoCapture(0)
    time.sleep(2)
    _, raw_image = capture1.read()
    (major_ver, minor_ver, subminor_ver) = (cv2.__version__).split('.')
    if int(major_ver)  < 3 :
        fps = capture1.get(cv2.cv.CV_CAP_PROP_FPS)
       
    else :
        fps = capture1.get(cv2.CAP_PROP_FPS)
    
    #cv2.imwrite('{}raw.png'.format(config.OUTPUT_PATH),raw_image)
    config.FPS=fps
    #logging.info("Start FPS: {}".format(fps))
    capture1.release()
    
    adapt_blur(raw_image)
   
    
    while True:
        ''' check room brightness '''
        capture = cv2.VideoCapture(0)
        time.sleep(2)
        _,sample=capture.read()

        config.INPUT_IMAGE_SIZE = raw_image.shape[:-1][::-1]
        hsv = cv2.cvtColor(sample.copy(), cv2.COLOR_BGR2HSV)
        avg_color_per_row = np.average(hsv, axis=0)
        avg_color = np.average(avg_color_per_row, axis=0)
        brightness = avg_color[2]
        
        
        if brightness > config.ROOM_BRIGHTNESS_THRESHOLD:
            capture.release()
            try:

                (change,count) = Record.start_recording(time.time(), raw_image)
                # print(coordinates)

                ''' imported function for calcuating the distance of a person from the objects '''
                f = open('{}outputTable{}.csv'.format(config.OUTPUT_PATH, time.strftime(
                    '%b-%d-%Y_%H%M%S', time.localtime())), "w")
                writer = csv.DictWriter(f, fieldnames=[
                    "Timestamp", "Furniture_Type", "Usage_Count", "Total_Checks", "Usage_Percentage", "Usage_Type", "Room_Occupancy", "Device_ID"])
                writer.writeheader()
                
                calculate_and_map(raw_image, change, writer, count)
                f.close()

                if(config.GOOGLE_DRIVE_UPLOAD_ALLOWED == 1 and connect() == True):
                    time.sleep(2)
                    create_zip('{}newRecording{}'.format(
                        config.OUTPUT_PATH, socket.gethostname()))
                    file_meta_data = {'name': 'newRecording{}'.format(socket.gethostname()), 'time': time.strftime(
                        '%b-%d-%Y_%H%M%S', time.localtime())}
                    results = upload_files('{}newRecording{}'.format(
                        config.OUTPUT_PATH, socket.gethostname()), file_meta_data)
                    print('File uploaded ID: {}'.format(results.get('id')))
                    logging.info(
                        'Files uploaded ID: {}'.format(results.get('id')))
                elif(connect() == False):
                    logging.info("Output files are being stored on local device because system is not connected to the internet!")

            except Exception as e:
                print(e)
                logging.error(e)

            if config.TEST_MODE == 1:
                logging.info(
                    'Testing! please set testMode to 0 in configuration file for full mode...')
                break
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        else:
            capture.release()
            print('The room is too dark for a photo!')
            logging.info('The room is too dark for a photo {}!'.format(
                time.strftime('%b-%d-%Y_%H%M%S', time.localtime())))
            if config.TEST_MODE == 0:
                time.sleep(config.SLEEP_DURATION)
            else:
                logging.info(
                    'testing!!! please set testMode to 0 in configuration file for full mode...')

                break
        # capture.release()
        cv2.destroyAllWindows()


def main():
    """main function"""
    logging.basicConfig(filename='{}LOWatch.log'.format(
        config.OUTPUT_PATH),format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S', level=logging.DEBUG)
    logging.getLogger('matplotlib.font_manager').disabled = True
    
    generate_map()


if __name__ == "__main__":
    main()

