var running = document.getElementById("running");
var alarm = document.getElementById("alarm");
var button_start = document.getElementById("button_start");
var button_stop = document.getElementById("button_stop");
var message = document.getElementById("message");
var network_table = document.getElementById("t_network");
var network_section = document.getElementById("s_network");

function show_message(msg) {
    message.innerHTML = msg;
    message.style.display = "block";
}

function clear_message() {
    message.style.display = "none";
}

function status_failed(xhr, status) {
    show_message("Failed to get status from detector.");
}

function clear_network_table() {
    network_table.children[1].innerHTML = "";
}

function update_page() {
    var xhr_status = new XMLHttpRequest();
    var xhr_networks = new XMLHttpRequest();

    xhr_status.onreadystatechange = function() {
        if (xhr_status.readyState == XMLHttpRequest.DONE) {
            if (xhr_status.status == 200) {
                var status = JSON.parse(this.responseText);
                clear_message();
                running.innerHTML = status.running;
                alarm.innerHTML = status.alarm;
            } else {
                status_failed(xhr_status, xhr_status.status);
            }
        }
    }
    xhr_status.onerror = function() {
        xhr_status_failed(xhr_status, xhr_status.status);
    }

    xhr_networks.onreadystatechange = function() {
        if (xhr_networks.readyState == XMLHttpRequest.DONE) {
            if (xhr_networks.status == 200) {
                var networks = JSON.parse(this.responseText);
                clear_network_table();
                tbody = network_table.children[1];

                if (networks.length == 0)
                    network_section.style.display = "none";
                else
                    network_section.style.display = "block";

                for (i=0; i < networks.length; i++) {
                    var row = tbody.insertRow(i);

                    for (j=0; j < networks[i][1].length; j++) {
                        c = row.insertCell(j);
                        c.innerHTML = networks[i][1][j];
                    }

                    if (networks[i][0])
                        row.setAttribute("class", "target");
                }
            } else {
                clear_network_table();
            }
        }
    }
    xhr_networks.onerror = function() {
        xhr_networks_failed(xhr_networks, xhr_networks.status);
    }

    // Needs to be > 2 seconds because that's approximately how
    // long a wifi scan takes.
    xhr_status.timeout = 5000;
    xhr_networks.timeout = 5000;

    xhr_status.open("GET", "/api/status");
    xhr_status.send();

    xhr_networks.open("GET", "/api/scan/result");
    xhr_networks.send();
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

var period = setInterval(update_page, 10000);
update_page();
