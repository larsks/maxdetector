function update_page() {
    var running = document.getElementById("running");
    var alarm = document.getElementById("alarm");
    var xhr = new XMLHttpRequest();

    xhr.onreadystatechange = function() {
        if (xhr.readyState == XMLHttpRequest.DONE) {
            var status = JSON.parse(this.responseText);
            running.innerHTML = status.running;
            alarm.innerHTML = status.alarm;
        }
    }

    xhr.open("GET", "/api/status");
    xhr.send();
}

var button_start = document.getElementById("button_start");
var button_stop = document.getElementById("button_stop");

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
