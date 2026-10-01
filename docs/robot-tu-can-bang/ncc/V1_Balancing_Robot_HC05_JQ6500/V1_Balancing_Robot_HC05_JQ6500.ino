/*
  BANLINHKIEN.COM 
  Ngày 15042025
  PROJECT: XE ROBOT CÂN BẰNG
  🤖 Phiên bản V1: Điều khiển Bluetooth HC05, phát âm thanh JQ6500
  🚀 Tính Năng Nổi Bật
    🧠 Tự động cân bằng: Ứng dụng thuật toán PID giúp robot luôn giữ trạng thái thăng bằng một cách chính xác và mượt mà.
    📱 Điều khiển từ xa qua Bluetooth:
      + Kết nối với HC-05 để điều khiển robot bằng app điện thoại (Android).
      + Điều khiển tiến, lùi, xoay trái, xoay phải qua giao diện app đơn giản và trực quan.
    🔊 Phát âm thanh sinh động:
      + Tích hợp JQ6500 + loa để phát nhạc hoặc âm thanh phản hồi khi thực hiện thao tác.
      + Có thể nạp sẵn 9 đoạn âm thanh yêu thích (mỗi đoạn dưới 10 giây)
    🌈 Hiệu ứng LED WS2812 (4 chiếc):
      - Tăng tính thẩm mỹ, dễ theo dõi trạng thái hoạt động.
      - Màu sắc hiển thị theo chế độ robot:
        + 🔴 Màu đỏ khi robot chưa sẵn sàng cân bằng.
        + 🌈 Hiệu ứng cầu vồng khi robot đã sẵn sàng hoạt động.
   

  ⚙️ Hướng Dẫn Sử Dụng
    - Khởi động robot đúng cách:
      + Đặt robot nằm ngang.
      + Bật công tắc nguồn.
      + Quan sát LED WS2812 chuyển từ đỏ sang cầu vồng.
      + Sau đó, từ từ dựng robot đứng lên.
    - Kết nối điều khiển:
      + Bật Bluetooth điện thoại, mở app điều khiển đã cài đặt.
      + Ghép nối với HC-05 (thường mật khẩu mặc định là 1234).
      + Sau khi kết nối thành công, dùng các nút trên app để điều khiển robot.
    - Âm thanh phản hồi:
      + Robot phát âm thanh tương ứng mỗi khi bạn gửi lệnh điều khiển.
      + Nạp file nhạc vào JQ6500 qua phần mềm chuyên dụng trên máy tính. Bạn hãy nạp 9 bài hát vào JQ6500, mỗi bài không quá 10s

  ⚠️ Lưu ý khi lập trình:
    - Tháo JQ6500 ra khỏi mạch trước khi nạp code cho Arduino.
    - Vì JQ6500 dùng chung TX/RX, tránh dùng Serial.print() trong chương trình nếu đang bật JQ6500.

  🔧 Thông Số Kỹ Thuật Chính
    - Vi điều khiển: Arduino Nano
    - Cảm biến: MPU6050 (IMU 6 trục)
    - Giao tiếp: HC-05 Bluetooth
    - Âm thanh: JQ6500 + loa 1W8R
    - Driver động cơ: A4988 + 2 Động Cơ Bước Nema17 42x38mm
    - LED: 4x WS2812 RGB
    - Còi: còi chip 5V
    - Nguồn cấp: 2 cell Li-ion 18650
  🔗 Tài liệu tham khảo
    👉 Tham khảo thuật toán điều khiển cân bằng từ Joop Brokking https://www.youtube.com/watch?v=6WWqo-Yr8lA&t=1s
*/
#include <Wire.h>                                           
#include <SoftwareSerial.h>
#include <Adafruit_NeoPixel.h>
#include <SimpleKalmanFilter.h>

//-------------------- Khai báo Button-----------------------
#include "mybutton.h"
#define BUTTON_SET_PIN    12
#define BUTTON1_ID  1
Button buttonSET;

void button_press_short_callback(uint8_t button_id);
void button_press_long_callback(uint8_t button_id);

// SimpleKalmanFilter kfilter(2, 2, 0.1);
#define NUMBER_SONGS 9

SoftwareSerial mySerial(9, 11); // RX, TX
// Khai báo led WS2812
const int ledPin = 11;                                        // Khai báo chân kết nối led WS2812
const int numLeds = 4 ;
Adafruit_NeoPixel strip = Adafruit_NeoPixel(numLeds, ledPin, NEO_GRB + NEO_KHZ800);
int count_loop = 0;
int count_loop_test = 0;
int gyro_address = 0x68;                                      // MPU-6050 I2C address 
int acc_calibration_value = 92;                              // Giá trị hiệu chỉnh gia tốc kế, lấy từ V0_0_Balancing_Hardware.ino

//Various settings 10/0.5/10
float pid_p_gain = 12;                                 // Cài đặt khuếch đại cho bộ điều khiển P 
float pid_i_gain = 0.4;                                // Cài đặt khuếch đại cho bộ điều khiển I
float pid_d_gain = 10;                                 // Cài đặt khuếch đại cho bộ điều khiển D
float turning_speed = 60;                              // Tốc độ xoay khi quay trái, quay phải
float max_target_speed = 150;                          // Tốc độ đi thẳng và lùi tối đa
char recieveData;                                      // Biến nhận data HC05
int delayLoop = 4000;
// Khai báo các biến toàn cục
byte start, received_byte, low_bat;

int left_motor, throttle_left_motor, throttle_counter_left_motor, throttle_left_motor_memory;
int right_motor, throttle_right_motor, throttle_counter_right_motor, throttle_right_motor_memory;
int battery_voltage;
int receive_counter;
int gyro_pitch_data_raw, gyro_yaw_data_raw, accelerometer_data_raw;
long gyro_yaw_calibration_value, gyro_pitch_calibration_value;

float angle_gyro, angle_acc, angle, self_balance_pid_setpoint;
float pid_error_temp, pid_i_mem, pid_setpoint, gyro_input, pid_output, pid_last_d_error;
float pid_output_left, pid_output_right;

byte switch_led = 0;
int music_song = 1;          
char lastRecieveData = 0;   // Lưu ký tự cuối cùng
uint8_t repeatCount = 0;    // Đếm số lần ký tự trùng liên tiếp
char validCommand = 0;      // Lệnh hợp lệ (được xác nhận sau 3 lần trùng)


typedef enum {
  MODE_BLUETOOTH,
  MODE_AVOID_OBJ
} MODE;
uint8_t modeRun = MODE_BLUETOOTH;

void rainbow(int index);
void wakeup();
void setVolume(int number);
void playMp3(int number);
unsigned long loop_timer;

// Khai báo chân động cơ A4988
#define STEP2       7            // D7    PORTD 7                 
#define STEP1       5            // D5    PORTD 5                                      
#define DIR2        6            // D6    PORTD 6                    
#define DIR1        4            // D4    PORTD 4 

//-------------------------------------------------------------------------------
/* Hàm khởi tạo timer2*/

void timer_init() {
  // Tạo một xung thay đổi để điều khiển động cơ bước, một bộ đếm thời gian được tạo ra sẽ thực thi một đoạn mã (chương trình con) cứ sau 20us
  // Chương trình con này được gọi là TIMER2_COMPA_vect
  TCCR2A = 0;                                                               // Đảm bảo rằng thanh ghi TCCR2A được đặt thành 0 (Timer/Counter Control Register A) Điều khiển chế độ hoạt động và đầu ra của Timer2.
  TCCR2B = 0;                                                               // Đảm bảo rằng thanh ghi TCCR2A được đặt thành 0 (Timer/Counter Control Register B) Điều khiển bộ chia xung (prescaler) và các chế độ khác.
  TCCR2B |= (1 << CS21);                                                    // Đặt bit CS21 trong thanh ghi TCCRB để đặt bộ chia trước Prescale thành 8
  OCR2A = 39;                                                               
  // Công thức tính tần số timer: fTimer = fCPU / Prescale. Với tần số CPU là 16MHZ và Prescale là 8 => fTimer = 16Mhz/8 = 2 Mzh => mỗi xung timer là 1/2Mhz = 0.5us
  // OCR2A (Output Compare Register A): Thanh ghi này chứa giá trị so sánh của Timer2. Khi bộ đếm Timer2 (TCNT2) đạt giá trị này, ngắt sẽ được kích hoạt.
  // Công thức tính T_interrupt = (OCR2A + 1) x T_tick, với OCR2A = 39, T_tick = 0.5us => T_interrupt = (39 + 1)x 0.5 = 20us
  TCCR2A |= (1 << WGM21);                                                   // Bộ đếm Timer2 (TCNT2) sẽ tăng dần từ 0 đến giá trị trong OCR2A (39).
                                                                            // Khi đạt giá trị OCR2A, bộ đếm sẽ tự động reset về 0 và tạo ra ngắt.
  TIMSK2 |= (1 << OCIE2A);                                                  // Cho phép ngắt xảy ra khi Timer2 đạt giá trị so sánh OCR2A.
                                                                            // Khi bộ đếm Timer2 khớp với OCR2A, ngắt sẽ được kích hoạt, và hàm xử lý ngắt tương ứng (TIMER2_COMPA_vect) sẽ được gọi.
}
//-------------------------------------------------------------------------------
// Hàm khởi tạo và tinh chỉnh cảm biến MPU6050
void mpu6050_init_calib() {
  //Theo mặc định MPU-6050 ở chế độ ngủ. Vì thế chúng ta phải đánh thức nó dậy.
  Wire.beginTransmission(gyro_address);                                     // Bắt đầu giao tiếp với MPU6050 với địa chỉ 0x68
  Wire.write(0x6B);                                                         // Ghi vào thanh ghi PWR_MGMT_1 (6B hex)
  Wire.write(0x00);                                                         // Đặt các bit là 00000000 để kích hoạt con quay hồi chuyển
  Wire.endTransmission();                                                   // Kết thúc quá trình truyền
  // Đặt thang đo đầy đủ của con quay hồi chuyển thành +/- 250 độ mỗi giây
  // Thiết lập độ nhạy thấp nhất, giúp dữ liệu mượt và ổn định hơn cho các chuyển động nhỏ.
  Wire.beginTransmission(gyro_address);                                     // Bắt đầu giao tiếp với MPU6050 với địa chỉ 0x68
  Wire.write(0x1B);                                                         // Ghi vào thanh ghi GYRO_CONFIG (1B hex)
  Wire.write(0x00);                                                         // Đặt các bit thanh ghi là 00000000 (250dps full scale)
  Wire.endTransmission();                                                   // Kết thúc quá trình truyền
  // Đặt thang đo đầy đủ của gia tốc kế thành +/- 4g.
  // Thiết lập phạm vi đo gia tốc, phù hợp cho ứng dụng cân bằng robot.
  Wire.beginTransmission(gyro_address);                                     // Bắt đầu giao tiếp với MPU6050 với địa chỉ 0x68
  Wire.write(0x1C);                                                         // Ghi vào thanh ghi ACCEL_CONFIG (1C hex)
  Wire.write(0x08);                                                         // Đặt bit là 00001000 (+/- 4g phạm vi toàn thang đo)
  Wire.endTransmission();                                                   // Kết thúc quá trình truyền
  // Đặt một số bộ lọc để cải thiện dữ liệu thô
  // Làm mượt dữ liệu đầu ra từ cảm biến, giảm nhiễu.
  Wire.beginTransmission(gyro_address);                                     // Bắt đầu giao tiếp với MPU6050 với địa chỉ 0x68
  Wire.write(0x1A);                                                         // Ghi vào thanh ghi CONFIG (1A hex)
  Wire.write(0x03);                                                         // Đặt bit là 00000011 (Đặt Bộ lọc thông thấp kỹ thuật số thành ~43Hz) Digital Low Pass Filter
  Wire.endTransmission();                                                   // Kết thúc quá trình truyền
  // Hiệu chỉnh MPU6050
  for(receive_counter = 0; receive_counter < 500; receive_counter++){       // Tạo 500 vòng lặp
    rainbow(85);
    Wire.beginTransmission(gyro_address);                                   // Bắt đầu giao tiếp với MPU6050 với địa chỉ 0x68
    Wire.write(0x43);                                                       // Đọc từ thanh ghi 0x43 (Gyro X).
    Wire.endTransmission();                                                 // Kết thúc quá trình truyền
    Wire.requestFrom(gyro_address, 4);                                      // Request 4 bytes từ MPU6050, byte (2 byte cho Yaw, 2 byte cho Pitch).
    gyro_yaw_calibration_value += Wire.read()<<8|Wire.read();               // Kết hợp hai byte để tạo thành một số nguyên
    gyro_pitch_calibration_value += Wire.read()<<8|Wire.read();             // Kết hợp hai byte để tạo thành một số nguyên
    delayMicroseconds(3700);                                                // Chờ 3700 micro giây để mô phỏng thời gian vòng lặp chương trình chính
  }
  // Chia tổng giá trị đọc được sau 500 lần lặp cho 500. Kết quả là giá trị offset cho con quay hồi chuyển.
  // Gyro thường có độ lệch nhỏ khi ở trạng thái tĩnh. Offset này giúp loại bỏ sai số trong các phép tính góc sau này.
  gyro_pitch_calibration_value /= 500;                                      
  gyro_yaw_calibration_value /= 500;                                       
}

void setup(){
  Serial.begin(9600);               // Khởi tạo serial 9600 kbps
  mySerial.begin(9600);             // Khởi tạo software serial cho module bluetooth HC05
  Wire.begin();                     // Khởi tạo I2C bus master
  TWBR = 12;                        // Cài đặt I2C clock speed 400kHz
  pinMode(STEP1, OUTPUT);           // Khởi tạo chân STEP cho động cơ 1
  pinMode(STEP2, OUTPUT);           // Khởi tạo chân STEP cho động cơ 2
  pinMode(DIR1, OUTPUT);            // Khởi tạo chân DIR cho động cơ 1
  pinMode(DIR2, OUTPUT);            // Khởi tạo chân DIR cho động cơ 2
  pinMode(13, OUTPUT);              // Khởi tạo LED

  resetMP3();                       // Reset JQ6500
  setVolume(10);                    // Cài đặt âm lượng âm thanh cho JQ6500
  delay(100);                 

  // Khởi tạo nút nhấn
  pinMode(BUTTON_SET_PIN, INPUT_PULLUP);                                  // Khai báo nút nhấn
  button_init(&buttonSET, BUTTON_SET_PIN, BUTTON1_ID);                    // Khởi tạo nút nhấn
  button_pressshort_set_callback((void *)button_press_short_callback);    // Khai báo hàm callback nhấn nhanh
  button_presslong_set_callback((void *)button_press_long_callback);      // Khai báo hàm callback nhấn giữ

  // Khởi tạo led ws2812
  strip.begin();                                    // Khởi tạo led ws2812
  strip.setBrightness(255);                         // Cài đặt độ sáng ws2812

  timer_init();                                     // Khởi tạo timer  
  mpu6050_init_calib();                             // Khởi tạo và tinh chỉnh mpu6050
 
  loop_timer = micros() + 4000;   
}

void loop(){
  count_loop += 1;
  if(count_loop >= 1000) count_loop = 0;

  if(count_loop % 50 == 0) {
    switch_led = 1 - switch_led;
  }

  // ===================== NHẬN DỮ LIỆU ===========================
  if (mySerial.available()) {
    recieveData = mySerial.read();
    if(recieveData == 'V') {                                             // Nếu byte nhận được là 'V' thì bật nhạc
      playMp3Index(music_song);
    }
    else if(recieveData == 'v') {
      resetMP3();                       // Reset JQ6500
      setVolume(10);                    // Cài đặt âm lượng âm thanh cho JQ6500
    }
    else if(recieveData == '1') {                                             // Nếu byte nhận được là '1' thì cài bài nhạc phát là 1
      music_song = 1;
    }
    else if(recieveData == '2') {                                             // Nếu byte nhận được là '2' thì cài bài nhạc phát là 2
      music_song = 2;
    }
    else if(recieveData == '3') {                                             // Nếu byte nhận được là '3' thì cài bài nhạc phát là 3
      music_song = 3;
    }
    else if(recieveData == '4') {                                             // Nếu byte nhận được là '4' thì cài bài nhạc phát là 4
      music_song = 4;
    }
    else if(recieveData == '5') {                                             // Nếu byte nhận được là '5' thì cài bài nhạc phát là 5
      music_song = 5;
    }
    else if(recieveData == '6') {                                             // Nếu byte nhận được là '6' thì cài bài nhạc phát là 6
      music_song = 6;
    }
    else if(recieveData == '7') {                                             // Nếu byte nhận được là '7' thì cài bài nhạc phát là 7
      music_song = 7;
    }
    else if(recieveData == '8') {                                             // Nếu byte nhận được là '8' thì cài bài nhạc phát là 8
      music_song = 8;
    }
    else if(recieveData == '9') {                                             // Nếu byte nhận được là '9' thì cài bài nhạc phát là 9
      music_song = 9;
    }

    receive_counter = 0;  // Reset timeout

    // Nếu ký tự giống ký tự trước -> tăng đếm
    if (recieveData == lastRecieveData) {
        repeatCount++;
      } else {
        repeatCount = 1; // reset nếu khác
      }
      lastRecieveData = recieveData;

      // Nếu trùng >= 3 lần thì xác nhận là lệnh hợp lệ
      if (repeatCount >= 3) {
        validCommand = recieveData;
      }
  }

  // Hết thời gian timeout thì reset
  if (receive_counter <= 25) receive_counter++;
  else {
    recieveData = 0x00;
    validCommand = 0x00;
    repeatCount = 0;
  }                                          //After 100 milliseconds the received byte is deleted
  // Serial.println(recieveData);
  // Đọc điện áp PIN, nếu dưới 6.4V thì cho ROBOT dừng hoạt động
  // Trở R1 10k, R2 5K , Vmax 8.4V = 2.8V, Vmin 6.4V = 2.1V = 430/1024
  battery_voltage = analogRead(A0);                                         // Đọc analog chân A0
  if(battery_voltage < 420) {                                               // Nếu điện áp < 6.4V
    low_bat = 1;                                                            // Set low_bat = 1
    led_blue();                                                             // Cho Led WS2812 sáng xanh dương
  }
  //-------------------------------------------------------------------------------
  // Tính toán góc nghiêng
  calculateAngle();

  // Tính toán bộ điều khiển PID
  // Robot cân bằng được điều khiển theo góc. Đầu tiên là sự khác biệt giữa góc mong muốn (setpoint) và góc thực tế (process value) được tính toán.
  // Biến self_balance_pid_setpoint được tự động thay đổi để đảm bảo robot luôn cân bằng.
  // Phần (pid_setpoint - pid_output * 0.015) hoạt động như một hàm phanh.
  pid_error_temp = angle_gyro - self_balance_pid_setpoint - pid_setpoint;
  if(pid_output > 10 || pid_output < -10) pid_error_temp += pid_output * 0.015 ;

  pid_i_mem += pid_i_gain * pid_error_temp;                                 // Tính toán giá trị bộ điều khiển I và thêm nó vào biến pid_i_mem
  if(pid_i_mem > 400)pid_i_mem = 400;                                       // Giới hạn bộ điều khiển I ở mức đầu ra bộ điều khiển tối đa
  else if(pid_i_mem < -400)pid_i_mem = -400;
  // Tính toán giá trị đầu ra PID
  // Giới hạn PID ở -400 đến -5, 5 đến 400. 
  // Vì 400 là giá trị điều khiển mà động cơ gần như quay rất chậm, 5 là giá trị mà động cơ quay nhanh, nếu nhanh hơn nữa sẽ trượt bước
  pid_output = pid_p_gain * pid_error_temp + pid_i_mem + pid_d_gain * (pid_error_temp - pid_last_d_error);
  if(pid_output > 400)pid_output = 400;                                     // Giới hạn bộ điều khiển PI ở mức đầu ra bộ điều khiển tối đa
  else if(pid_output < -400)pid_output = -400;

  pid_last_d_error = pid_error_temp;                                        // Lưu trữ giá trị error cho vòng lặp tiếp theo

  if(pid_output < 5 && pid_output > -5)pid_output = 0;                      // Giới hạn giá trị đầu ra

  if(angle_gyro > 30 || angle_gyro < -30 || start == 0 || low_bat == 1){    // Nếu robot bị lật hoặc biến start = 0 hoặc pin hết
    pid_output = 0;                                                         // Đặt đầu ra của bộ điều khiển PID thành 0 để động cơ ngừng chuyển động
    pid_i_mem = 0;                                                          // Thiết lập lại bộ nhớ bộ điều khiển I
    start = 0;                                                              // Đặt biến start = 0
    self_balance_pid_setpoint = 0;                                          // Đặt lại biến self_balance_pid_setpoint
  }
  //-------------------------------------------------------------------------------
  // Kiểm soát tính toán cho từng bên động cơ
  pid_output_left = pid_output;                                             // Sao chép đầu ra của bộ điều khiển vào biến pid_output_left cho động cơ bên trái
  pid_output_right = pid_output;                                            // Sao chép đầu ra của bộ điều khiển vào biến pid_output_right cho động cơ bên phải
  // Serial.println(recieveData);
  //-------------------------------------------------------------------------------
  // Xử lí tín hiệu từ module HC05
  if(validCommand  == 'R'){                                                   // Nếu byte nhận được là 'R' thì quay phải
    pid_output_left += turning_speed;                                       // Tăng tốc độ động cơ bên trái
    pid_output_right -= 2*turning_speed;                                      // Giảm tốc độ động cơ bên phải
    blink_led(1,switch_led);                                                // Nháy 2 LED WS2812 bên phải
  }
  else if(validCommand  == 'L'){                                              // Nếu byte nhận được là 'L' thì quay trái
    pid_output_left -= 2*turning_speed;                                       // Giảm tốc độ động cơ bên trái
    pid_output_right += turning_speed;                                      // Tăng tốc độ động cơ bên phải
    blink_led(-1,switch_led);
  }
  else if(validCommand  == 'B'){                                              // Nếu byte nhận được là 'F' thì đi thẳng
    if(pid_setpoint > -2.5)pid_setpoint -= 0.05;                            // Từ từ thay đổi góc đặt để robot bắt đầu nghiêng về phía trước
    if(pid_output > max_target_speed * -1)pid_setpoint -= 0.005;            // Từ từ thay đổi góc đặt để robot bắt đầu nghiêng về phía trước
    blink_led(0,switch_led);
  }
  else if(validCommand  == 'F'){                                              // Nếu byte nhận được là 'B' thì đi lùi
    if(pid_setpoint < 2.5)pid_setpoint += 0.05;                             // Từ từ thay đổi góc đặt để robot bắt đầu nghiêng về phía sau
    if(pid_output < max_target_speed)pid_setpoint += 0.005;                 // Từ từ thay đổi góc đặt để robot bắt đầu nghiêng về phía sau
    blink_led(2,switch_led);
  }   
  else if(validCommand   == 'S'){                                             // Nếu byte nhận được là 'S', giảm dần điểm đặt xuống 0 nếu không có lệnh tiến hoặc lùi nào được đưa ra
    if(pid_setpoint > 0.5)pid_setpoint -=0.05;                              // Nếu điểm đặt PID lớn hơn 0,5 thì giảm điểm đặt xuống 0,05 sau mỗi vòng lặp
    else if(pid_setpoint < -0.5)pid_setpoint +=0.05;                        // Nếu điểm đặt PID nhỏ hơn -0,5 thì tăng điểm đặt thêm 0,05 sau mỗi vòng lặp
    else pid_setpoint = 0;                                                  // Nếu điểm đặt PID nhỏ hơn 0,5 hoặc lớn hơn -0,5 thì đặt điểm đặt thành 0
    if(count_loop % 4 == 0)                                                 // Nháy led cầu vồng
      rainbow(count_loop / 4);
  }
  else if(validCommand   == 0 ){                                              // Nếu không có data HC05 thì cho nháy led cầu vồng
    if(count_loop % 4 == 0)
      rainbow(count_loop / 4);
  }
  
  //-------------------------------------------------------------------------------
  // Điểm tự cân bằng được điều chỉnh khi không có chuyển động tiến hoặc lùi từ bộ truyền. Theo cách này, robot sẽ luôn tìm thấy điểm cân bằng của nó
  if(pid_setpoint == 0){                                                    // Nếu điểm đặt là 0 độ
    if(pid_output < 0)self_balance_pid_setpoint += 0.002;                  // Tăng self_balance_pid_setpoint nếu robot vẫn đang di chuyển về phía trước
    if(pid_output > 0)self_balance_pid_setpoint -= 0.002;                  // Giảm self_balance_pid_setpoint nếu robot vẫn đang di chuyển lùi
  }
  //-------------------------------------------------------------------------------
  // Tính toán xung động cơ
  // Để bù cho hành vi phi tuyến tính của động cơ bước, cần thực hiện các phép tính sau để có được hành vi tốc độ tuyến tính.
  if(pid_output_left > 0)pid_output_left = 405 - (1/(pid_output_left + 9)) * 5500;
  else if(pid_output_left < 0)pid_output_left = -405 - (1/(pid_output_left - 9)) * 5500;

  if(pid_output_right > 0)pid_output_right = 405 - (1/(pid_output_right + 9)) * 5500;
  else if(pid_output_right < 0)pid_output_right = -405 - (1/(pid_output_right - 9)) * 5500;

  // Tính toán thời gian xung cần thiết cho bộ điều khiển động cơ bước trái và phải
  if(pid_output_left > 0)left_motor = 400 - pid_output_left;
  else if(pid_output_left < 0)left_motor = -400 - pid_output_left;
  else left_motor = 0;

  if(pid_output_right > 0)right_motor = 400 - pid_output_right;
  else if(pid_output_right < 0)right_motor = -400 - pid_output_right;
  else right_motor = 0;

  // Sao chép thời gian xung vào các biến điều tiết để chương trình con ngắt có thể sử dụng chúng
  throttle_left_motor = left_motor;
  throttle_right_motor = right_motor;

  handle_button(&buttonSET);
  while(loop_timer > micros());
  loop_timer += 4000;
}

//-------------------------------------------------------------------------------
// Tính toán góc nghiêng
void calculateAngle(){
  Wire.beginTransmission(gyro_address);                                    // Bắt đầu giao tiếp MPU6050
  Wire.write(0x3F);                                                         // Bắt đầu đọc ở register 3F
  Wire.endTransmission();                                                   // Kết thúc truyền
  Wire.requestFrom(gyro_address, 2);                                        // Yêu cầu 2 byte từ MPU6050
  accelerometer_data_raw = Wire.read()<<8|Wire.read();                      // Kết hợp hai byte để tạo thành một số nguyên
  accelerometer_data_raw += acc_calibration_value;                          // Thêm giá trị hiệu chuẩn gia tốc kế
  if(accelerometer_data_raw > 8200)accelerometer_data_raw = 8200;           // Giới hạn dữ liệu gia tốc kế thô +/-8200;
  if(accelerometer_data_raw < -8200)accelerometer_data_raw = -8200;         // Giới hạn dữ liệu gia tốc kế thô +/-8200;
  
  // (float)accelerometer_data_raw / 8200.0: Chuyển giá trị gia tốc về dạng số thực và chuẩn hóa trong khoảng -1 đến 1.
  // asin(...): Tính arcsin để lấy góc nghiêng từ giá trị gia tốc.
  // * 57.296: Chuyển từ radian sang độ (1 rad ≈ 57.296 độ).
  angle_acc = asin((float)accelerometer_data_raw/8200.0)* 57.296;           // Tính toán góc hiện tại theo gia tốc kế

  if(start == 0 && angle_acc > -0.5&& angle_acc < 0.5){                     // Nếu góc gia tốc kế gần bằng 0
    angle_gyro = angle_acc;                                                 // Ghi góc gia tốc kế vào biến angle_gyro
    start = 1;                                                              // Đặt biến start = 0 để khởi động bộ điều khiển PID
  }
  
  Wire.beginTransmission(gyro_address);                                     // Bắt đầu giao tiếp MPU6050
  Wire.write(0x43);                                                         // Bắt đầu đọc ở register 43
  Wire.endTransmission();                                                   // Kết thúc truyền
  Wire.requestFrom(gyro_address, 4);                                        // Yêu cầu 4 byte từ MPU6050. Dữ liệu từ thanh ghi 0x43 (Yaw) và 0x45 (Pitch).
  gyro_yaw_data_raw = Wire.read()<<8|Wire.read();                           // Kết hợp từng cặp byte để tạo giá trị 16-bit cho gyro_yaw_data_raw và gyro_pitch_data_raw.
  gyro_pitch_data_raw = Wire.read()<<8|Wire.read();                         
  
  // Tính Góc Từ Con Quay Hồi Chuyển
  // Bù trừ offset MPU-6050 offset
  // Không phải mọi con quay hồi chuyển đều được gắn ở mức 100% với trục của robot. Điều này có thể do sự sai lệch trong quá trình sản xuất.
  // Kết quả là robot sẽ không quay ở cùng một vị trí chính xác mà bắt đầu tạo ra những vòng tròn ngày càng lớn hơn.
  // Để bù đắp cho hành vi này, cần phải bù góc RẤT NHỎ khi robot quay.
  // Trước tiên hãy thử 0,0000003 hoặc -0,0000003 để xem có cải thiện gì không.
  gyro_pitch_data_raw -= gyro_pitch_calibration_value;                      // Thêm giá trị hiệu chuẩn con quay hồi chuyển
  angle_gyro += gyro_pitch_data_raw * 0.000031;                             

  gyro_yaw_data_raw -= gyro_yaw_calibration_value;                          // Thêm giá trị hiệu chuẩn con quay hồi chuyển
  //Uncomment the following line to make the compensation active
  angle_gyro -= gyro_yaw_data_raw * 0.0000003;                              // Bù trừ độ lệch con quay hồi chuyển khi robot đang quay

  angle_gyro = angle_gyro * 0.9996 + angle_acc * 0.0004;                    // Hiệu chỉnh độ trôi của góc con quay hồi chuyển bằng góc gia tốc kế
  // Serial.println(angle_gyro);
}
// --------------------------------------------------------------
// Các hàm xử lí âm thanh JQ6500
// Hàm bật bài hát theo index
void playMp3Index(int number) {
  Serial.write(0x7E);
  Serial.write(0x04);
  Serial.write(0x03);
  Serial.write(0x00);
  Serial.write(number);
  Serial.write(0xEF);
}
// Cài âm lượng âm thanh
void setVolume(int number){
  if(number<0) number = 0;
  if(number>30) number = 0;
  Serial.write(0x7E);
  Serial.write(0x03);
  Serial.write(0x06);
  Serial.write(number);
  Serial.write(0xEF);
}
// Dừng bài hát
void pauseMP3(){
  Serial.write(0x7E);
  Serial.write(0x02);
  Serial.write(0x0E);
  Serial.write(0xEF);
}
// Reset module
void resetMP3(){
  Serial.write(0x7E);
  Serial.write(0x02);
  Serial.write(0x0C);
  Serial.write(0xEF);
}
// Bật bài hát
void playMP3(){
  Serial.write(0x7E);
  Serial.write(0x02);
  Serial.write(0x0D);
  Serial.write(0xEF);
}
// --------------------------------------------------------------
// Các hàm hiệu ứng led WS2812
// Hàm tạo hiệu ứng cầu vồng
void rainbow(int index) {
  uint16_t i;
  for(i=0; i<strip.numPixels(); i++) {
    strip.setPixelColor(i, wheel((i*1 + index) & 255));
  }
  strip.show();
}
// Hàm set led màu xanh dương
void led_blue(){
  uint16_t i;
  for(i=0; i<strip.numPixels(); i++) {
    strip.setPixelColor(i, strip.Color(0, 0, 255));
  }
  strip.show();
}
// Hàm set led màu xanh lá cây
void led_green(){
  uint16_t i;
  for(i=0; i<strip.numPixels(); i++) {
    strip.setPixelColor(i, strip.Color(0, 0, 255));
  }
  strip.show();
}
// Hàm nháy led
void blink_led(int direct, int onoff) { 
  int color = 0;
  int color2 = 0;
  if(onoff == 1) {
    color = 255;
    color2 = 128;
  }
  if(onoff == 0) color = 0;
  if(direct == 0) {
    strip.setPixelColor(0, strip.Color(color, color2, 0));
    strip.setPixelColor(1, strip.Color(color, color2, 1));
  }
  else if(direct == 1) {
    strip.setPixelColor(0, strip.Color(color, color2, 0));
    strip.setPixelColor(3, strip.Color(color, color2, 0));
  }
  else if(direct == 2) {
    strip.setPixelColor(2, strip.Color(color, color2, 0));
    strip.setPixelColor(3, strip.Color(color, color2, 1));
  }
   else if(direct == -1) {
    strip.setPixelColor(1, strip.Color(color, color2, 0));
    strip.setPixelColor(2, strip.Color(color, color2, 0));
  }
  strip.show();
}
uint32_t wheel(byte WheelPos) {
  if(WheelPos < 85) {
    return strip.Color(WheelPos * 3, 255 - WheelPos * 3, 0);
  } 
  else if(WheelPos < 170) {
    WheelPos -= 85;
    return strip.Color(255 - WheelPos * 3, 0, WheelPos * 3);
  } 
  else {
    WheelPos -= 170;
    return strip.Color(0, WheelPos * 3, 255 - WheelPos * 3);
  }
}
// -------------------------------------------------------------------------
// Hàm ngắt TIMER2
// Ta lấy giá trị throttle_left_motor và throttle_right_motor từ bên trên hàm main
// Khi đó, giá trị throttle_left_motor và throttle_right_motor càng nhỏ thì động cơ quay càng nhanh
// vì biến đếm được reset nhanh hơn
// Lấy ví dụ: throttle_right_motor = 5
// B1: Ở ngắt đầu tiên, ban đầu throttle_right_motor_memory = 0; throttle_counter_right_motor = 0;
// B2: throttle_counter_right_motor++; Khi đó throttle_counter_right_motor = 1
// B3: throttle_counter_right_motor > throttle_right_motor_memory; 1 > 0 nên đúng, vào bên trong
// B4: throttle_counter_right_motor = 0;
//     throttle_right_motor_memory = throttle_right_motor = 5;
//     Do throttle_right_motor_memory = 5 > 0 => set động cơ quay thuận
// B5: Ở ngắt thứ 2: throttle_counter_right_motor++; =>  throttle_counter_right_motor = 1;
// B6: throttle_counter_right_motor = 1 < throttle_right_motor_memory = 5: nên sai
// B7: Chương trình vào else if(throttle_counter_right_motor == 1) sau đó xuất chân step lên cao
// B8: Ở ngắt thứ 3, throttle_counter_right_motor++; => throttle_counter_right_motor = 2; sau đó xuất chân step xuống thấp
// B9: Đợi tiếp cho đến khi throttle_counter_right_motor++ lên 6 > throttle_right_motor_memory = 5, thì lại tiếp tục B1
// Như vậy ta thấy nếu throttle_right_motor = 400 thì nó chỉ xuất xung ở throttle_counter_right_motor == 1, tắt xung ở throttle_counter_right_motor == 2
// và đợi cho đến khi throttle_counter_right_motor ++ == 401. 
// ===> Xuất xung càng chậm thì tốc độ càng chậm, xuất xung càng nhanh thì tốc độ càng nhanh
ISR(TIMER2_COMPA_vect){
  // Tính toán xung động cơ bên trái
  throttle_counter_left_motor ++;                                           // Tăng biến throttle_counter_left_motor lên 1 mỗi lần thực hiện quy trình này
  if(throttle_counter_left_motor > throttle_left_motor_memory){             // Nếu số vòng lặp lớn hơn thì biến throttle_left_motor_memory
    throttle_counter_left_motor = 0;                                        // Đặt lại biến throttle_counter_left_motor
    throttle_left_motor_memory = throttle_left_motor;                       // Lưu biến throttle_left_motor vào throttle_left_motor_memory
    if(throttle_left_motor_memory < 0){                                     // Nếu throttle_left_motor_memory là số âm
      PORTD |= 0b01000000;                                                  // Ghi chân DIR2 D6 ở mức cao cho hướng tiến của động cơ bước
      throttle_left_motor_memory *= -1;                                     // Đảo ngược biến throttle_left_motor_memory
    }
    else 
      PORTD &= 0b10111111;                                                  // Ghi chân DIR2 D6 ở mức thấp để đảo ngược hướng của bộ điều khiển bước
  }
  else if(throttle_counter_left_motor == 1)
    PORTD |= 0b10000000;                                                    // Ghi chân STEP2 D7 ở mức cao để tạo xung cho bộ điều khiển bước     
  else if(throttle_counter_left_motor == 2)
    PORTD &= 0b01111111;                                                    // Ghi chân STEP2 D7 ở mức thấp vì xung chỉ kéo dài trong 20us            
  
  // Tính toán xung động cơ bên phải
  throttle_counter_right_motor ++;                                          // Tăng biến throttle_counter_right_motor lên 1 mỗi lần thực hiện quy trình
  if(throttle_counter_right_motor > throttle_right_motor_memory){           // Nếu số vòng lặp lớn hơn thì biến throttle_right_motor_memory
    throttle_counter_right_motor = 0;                                       // Đặt lại biến throttle_counter_right_motor
    throttle_right_motor_memory = throttle_right_motor;                     // Lưu biến throttle_right_motor vào throttle_right_motor_memory
    if(throttle_right_motor_memory < 0){                                    // Nếu throttle_right_motor_memory là số âm
        PORTD &= 0b11101111;                                                // Ghi chân DIR1 D4 ở mức thấp để đảo ngược hướng của bộ điều khiển bước
      throttle_right_motor_memory *= -1;                                    // Đảo ngược biến throttle_right_motor_memory
    }
    else 
        PORTD |= 0b00010000;                                                // Ghi chân DIR1 D4 ở mức cao cho hướng tiến của động cơ bước
  }
  else if(throttle_counter_right_motor == 1) 
    PORTD |= 0b00100000 ;                                                   // Ghi chân STEP1 D5 mức cao để tạo xung cho bộ điều khiển bước
  else if(throttle_counter_right_motor == 2)
    PORTD &= 0b11011111;                                                    // Ghi chân STEP1 D5 mức thấp vì xung chỉ kéo dài trong 20us
}

//-----------------Hàm xử lí nút nhấn nhả ----------------------
void button_press_short_callback(uint8_t button_id) {
    switch(button_id) {
      case BUTTON1_ID :  
        Serial.println("btSET press short");
        playMp3Index(music_song);
        break;
    } 
} 
//-----------------Hàm xử lí nút nhấn giữ ----------------------
void button_press_long_callback(uint8_t button_id) {
  switch(button_id) {
    case BUTTON1_ID :
      Serial.println("btSET press long");
      break;

  } 
} 
