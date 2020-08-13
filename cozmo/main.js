//
//  COZMO controller
//

// global
var info;
var flg_run = true;
var main_loop_interval = 1000 / 30;
var last_key = '';
var cozmo_server = 'http://rp3-01.local:3141/';    // COZMO server URL
var cozmo_camera_interval = 1000 / 10;             // cozmo camera interval
var flg_stop_camera = true;
var cozmo_move_speed_def = 30;                     // defalut cozmo movement speed [0 - 100]
var cozmo_move_speed = cozmo_move_speed_def;       // cozmo movement speed [0 - 100]

// main function
window.onload = function()
{
    // setup event handler
    window.addEventListener('keydown', on_key_down);
    window.addEventListener('keyup', on_key_up);

    // element
    info = document.getElementById('info_txt');

    // setup buttons
    setup_button();

    // main loop
    ( function() {
        // update HTML
        info.innerHTML = 'Event [ ' + last_key + ' ]';

        // recursive call
        if ( flg_run ) { setTimeout(arguments.callee, main_loop_interval); }
    } ) ();
};

function on_key_down( event ) {
    // get keycode
    var ck = event.code;

    // check ESC key
    if ( ck === 'Escape' ) {
        flg_run = false;
    } else if ( ck === 'ArrowUp' ) {
        post_command('move', cozmo_move_speed);
    } else if ( ck === 'ArrowDown' ) {
        post_command('move', -cozmo_move_speed);
    } else if ( ck === 'ArrowLeft' ) {
        post_command('turn', -cozmo_move_speed);
    } else if ( ck === 'ArrowRight' ) {
        post_command('turn', cozmo_move_speed);
    } else if ( ck === 'Digit1' ) {
        post_command('lift', 'up');
    } else if ( ck === 'Digit2' ) {
        post_command('lift', 'down');
    } else if ( ck === 'Digit3' ) {
        post_command('head', 'up');
    } else if ( ck === 'Digit4' ) {
        post_command('head', 'down');
    } else if ( ck === 'Digit5' ) {
        if ( flg_stop_camera ) start_camera();
        else stop_camera();
    } else if ( ck === 'Digit6' ) {
        post_command('camera', 'raspi');
        setTimeout("reload_raspi_camera_image()", 1000);
    }

    last_key = event.code;
}

function on_key_up( event ) {
    // get keycode
    var ck = event.code;

    post_command('motor_stop', '0');

    last_key = '';
}

function setup_button() {
    var btnForward  = document.getElementById("btnForward");
    var btnLeft     = document.getElementById("btnLeft");
    var btnRight    = document.getElementById("btnRight");
    var btnReverse  = document.getElementById("btnReverse");
    var btnLiftUp   = document.getElementById("btnLiftUp");
    var btnLiftDown = document.getElementById("btnLiftDown");
    var btnHeadUp   = document.getElementById("btnHeadUp");
    var btnHeadDown = document.getElementById("btnHeadDown");
    var btnCameraOn = document.getElementById("btnCameraOn");
    var btnCameraOff = document.getElementById("btnCameraOff");
    var btnRaspiCamera = document.getElementById("btnRaspiCamera");
    var btnAnimation = document.getElementById("btnAnimation");
    var btnSetFace  = document.getElementById("btnSetFace");

    // button pressed
    btnForward.onmousedown = function () {
        post_command('move', cozmo_move_speed);
    }

    btnLeft.onmousedown = function () {
        post_command('turn', -cozmo_move_speed);
    }

    btnRight.onmousedown = function () {
        post_command('turn', cozmo_move_speed);
    }

    btnReverse.onmousedown = function () {
        post_command('move', -cozmo_move_speed);
    }

    btnLiftUp.onmousedown = function () {
        post_command('lift', 'up');
    }
    btnLiftDown.onmousedown = function () {
        post_command('lift', 'down');
    }

    btnHeadUp.onmousedown = function () {
        post_command('head', 'up');
    }
    btnHeadDown.onmousedown = function () {
        post_command('head', 'down');
    }

    // button released
    btnForward.onmouseup = function () {
        post_command('motor_stop', '0');
    }

    btnLeft.onmouseup = function () {
        post_command('motor_stop', '0');
    }

    btnRight.onmouseup = function () {
        post_command('motor_stop', '0');
    }

    btnReverse.onmouseup = function () {
        post_command('motor_stop', '0');
    }

    btnLiftUp.onmouseup = function () {
        post_command('motor_stop', '0');
    }
    btnLiftDown.onmouseup = function () {
        post_command('motor_stop', '0');
    }

    btnHeadUp.onmouseup = function () {
        post_command('motor_stop', '0');
    }
    btnHeadDown.onmouseup = function () {
        post_command('motor_stop', '0');
    }

    // button click
    btnCameraOn.onclick = function () {
        start_camera();
    }
    btnCameraOff.onclick = function () {
        stop_camera();
    }
    btnRaspiCamera.onclick = function () {
        post_command('camera', 'raspi');
        setTimeout("reload_raspi_camera_image()", 1000);
    }
    btnAnimation.onclick = function () {
        var anim_select = document.getElementById("anim_select");
        post_command('animation', anim_select.options[anim_select.selectedIndex].value);
    }
    btnSetFace.onclick = function () {
        var face_select = document.getElementById("face_select");
        post_command('face', face_select.options[face_select.selectedIndex].value);
    }

}

// post command to COZMO server
function post_command(cmd, val) {
    var json_asocc = {
                'command' : cmd,
                'value' : val
            };
     
    // encode to JSON format
    var json_text = JSON.stringify(json_asocc);
 
    // send data
    xhr = new XMLHttpRequest;

    xhr.onload = function() {
        var res = xhr.responseText;
        if ( res.length > 0 ) {
            var data = JSON.parse(res);
            update_status_panel(data);
        }
    }

    xhr.onerror = function() {
//        alert("error!");
    }

    xhr.open('POST', cozmo_server, true);
    xhr.withCredentials = true;
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.send(json_text);
}

// update status panel
function update_status_panel(data) {
    pose_txt = document.getElementById('pose_txt');
    pose_txt.innerHTML = '(' + data.pose_x.toFixed(1) + ', ' + data.pose_y.toFixed(1) + ', ' + data.pose_z.toFixed(1) + ') - [' +
        data.pose_angle_rad.toFixed(3) + ', ' + data.pose_pitch_rad.toFixed(3) + ']';

    wheel_txt = document.getElementById('wheel_txt');
    wheel_txt.innerHTML = '(' + data.lwheel_speed_mmps.toFixed(1) + ', ' + data.rwheel_speed_mmps.toFixed(1) + ')';

    head_txt = document.getElementById('head_txt');
    head_txt.innerHTML = data.head_angle_rad.toFixed(3);

    lift_txt = document.getElementById('lift_txt');
    lift_txt.innerHTML = data.lift_height_mm.toFixed(3);

    accel_txt = document.getElementById('accel_txt');
    accel_txt.innerHTML = '(' + data.accel_x.toFixed(1) + ', ' + data.accel_y.toFixed(1) + ', ' + data.accel_z.toFixed(1) + ') - [' +
        data.gyro_x.toFixed(3) + ', ' + data.gyro_y.toFixed(3) + ', ' + data.gyro_z.toFixed(3) + ']';

    status_txt = document.getElementById('status_txt');
    status_txt.innerHTML = data.status.toString(16);

    battery_txt = document.getElementById('battery_txt');
    battery_txt.innerHTML = data.battery_voltage.toFixed(1);

    touch_txt = document.getElementById('touch_txt');
    touch_txt.innerHTML = data.backpack_touch_sensor_raw.toString(16);

    cliff_txt = document.getElementById('cliff_txt');
    cliff_txt.innerHTML = data.cliff_data_raw;
}

// start camera
function start_camera() {
    flg_stop_camera = false;
    load_camera_image();
}

// stop camera
function stop_camera() {
    flg_stop_camera = true;
}

function load_camera_image() {
    xhr = new XMLHttpRequest;

    xhr.onload = function() {
        var oURL = URL.createObjectURL(this.response);
        camera_elem = document.getElementById('camera');
        camera_elem.src = oURL;
    };

    xhr.onerror = function() {
//        alert("error!");
    }

    xhr.responseType = "blob";
    xhr.open('GET', cozmo_server + 'camera.jpg', true);
    xhr.withCredentials = true;
    xhr.send();

    if ( !flg_stop_camera ) setTimeout("load_camera_image()", cozmo_camera_interval);
}

function reload_raspi_camera_image() {
    now = new Date();

    camera2_elem = document.getElementById('camera2');
    camera2_elem.src = "../camera2.jpg?" + now.getTime();
}
