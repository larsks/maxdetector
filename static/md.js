var running = document.getElementById("running");
var alarm = document.getElementById("alarm");
var message = document.getElementById("message");

var t_network = document.getElementById("t_network");
var s_network = document.getElementById("s_network");
var s_target = document.getElementById("s_target");
var t_target = document.getElementById("t_target");

function show_message(msg) {
    message.innerHTML = msg;
    message.style.display = "block";
}

function clear_message() {
    message.style.display = "none";
}

function update_page() {
    Promise.all([
        // Update running and alarm status
        fetch('/api/status')
        .then((response) => {
            return response.json();
        })
        .then((data) => {
            clear_message();
            running.innerHTML = data.running;
            alarm.innerHTML = data.alarm;
            return true;
        })
        .catch((error) => {
            console.log("failed to get status");
        }),

        // Get list of visible networks
        fetch('/api/scan/result')
        .then((response) => {
            return response.json();
        })
        .then((networks) => {
            var tbody = t_network.children[1];
            var i = 0;
            tbody.innerHTML = '';

            if (networks.length > 0) {
                networks.forEach((network) => {
                    var row = tbody.insertRow(i++);
                    var j = 0;
                    if (network[0])
                        row.setAttribute("class", "target");

                    network[1].forEach((item) => {
                        var cell = row.insertCell(j++);
                        cell.innerHTML = item;
                    });

                    // Adds "+" or "-" buttons to add/remove listed network
                    // from the list of targets.
                    var action = row.insertCell(j++);
                    if (! network[0]) {
                        action.innerHTML="<button class='action'>+</button>";
                        action.addEventListener("click", (event) => {
                            fetch("/api/target", {
                                method: "POST",
                                body: `target=${network[1][1]}`
                            });
                            update_page();
                        });
                    } else {
                        action.innerHTML="<button class='action'>-</button>";
                        action.addEventListener("click", (event) => {
                            fetch(`/api/target/${network[1][1]}`, {
                                method: "DELETE"
                            });
                            update_page();
                        });
                    }
                });
                s_network.style.display = "block";
            } else {
                s_network.style.display = "none";
            }

            return true;
        })
        .catch((error) => {
            console.log("failed to get list of visible networks");
        }),

        // Get list of targets
        fetch('/api/target')
        .then((response) => {
            return response.json();
        })
        .then((targets) => {
            var tbody = t_target.children[1];
            tbody.innerHTML = '';

            if (targets.length > 0) {
                s_target.style.display = "block";
                var i = 0;
                targets.forEach((target) => {
                    var row = tbody.insertRow(i++);
                    var cell = row.insertCell(0);
                    cell.innerHTML = target;

                    // Add "-" button for removing target.
                    cell = row.insertCell(1);
                    cell.innerHTML="<button class='action'>-</button>";
                    cell.addEventListener("click", (event) => {
                        fetch(`/api/target/${target}`, {
                            method: "DELETE"
                        });
                        update_page();
                    });
                });
            } else {
                s_target.style.display = "none";
            }
            return true;
        })
        .catch((error) => {
            console.log("failed to get list of targets");
        }),
    ])

    // see if any of the above operations failed and if so
    // show a message in the ui
    .then((values) => {
        var error = false;
        values.forEach((result) => {
            if (! result) error = true;
        })

        if (error)
            show_message("Failed to communicate with detector.");
        else
            clear_message();
    })
}

document.getElementById("button_start").addEventListener("click", function () {
    fetch('/api/scan/start')
        .then((response) => {
            update_page();
        })
});

document.getElementById("button_stop").addEventListener("click", function () {
    fetch('/api/scan/stop')
        .then((response) => {
            update_page();
        })
});

var period = setInterval(update_page, 10000);
update_page();
