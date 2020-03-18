var running = document.getElementById("running");
var alarm = document.getElementById("alarm");
var button_start = document.getElementById("button_start");
var button_stop = document.getElementById("button_stop");
var message = document.getElementById("message");

function show_message(msg) {
    message.innerHTML = msg;
    message.style.display = "block";
}

function clear_message() {
    message.style.display = "none";
}

function xhr_failed(xhr, status) {
    show_message(`Failed to get status from detector (${status}).`);
}

function update_page() {
    var xhr = new XMLHttpRequest();

    xhr.onreadystatechange = function() {
        if (xhr.readyState == XMLHttpRequest.DONE) {
            if (xhr.status == 200) {
                var status = JSON.parse(this.responseText);
                clear_message();
                running.innerHTML = status.running;
                alarm.innerHTML = status.alarm;
            } else {
                xhr_failed(xhr, xhr.status);
            }
        }
    }
    xhr.onerror = function() {
        xhr_failed(xhr, xhr.status);
    }

    // Needs to be > 2 seconds because that's approximately how
    // long a wifi scan takes.
    xhr.timeout = 5000;

    xhr.open("GET", "/api/status");
    xhr.send();
}

button_start.addEventListener("click", function () {
    var xhr = new XMLHttpRequest();
    xhr.onreadystatechange = function() {
        if (xhr.readyState == XMLHttpRequest.DONE) {
            update_page();
        }
    }

    xhr.open("GET", "/api/scan/start");
    xhr.send();
}, false);

button_stop.addEventListener("click", function () {
    var xhr = new XMLHttpRequest();
    xhr.onreadystatechange = function() {
        if (xhr.readyState == XMLHttpRequest.DONE) {
            update_page();
        }
    }

    xhr.open("GET", "/api/scan/stop");
    xhr.send();
}, false);

var period = setInterval(update_page, 5000);
update_page();
