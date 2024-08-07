let startTime;
let elapsedTime = 0;
let running = false;
let timer;
const timerElement = document.getElementById('timer');
let scrambleString = '';

// Function to get session ID from the URL or another method
function getSessionId() {
    // Example: Assuming the session ID is passed via a data attribute in the HTML
    const sessionIdElement = document.getElementById('session-id');
    return sessionIdElement ? sessionIdElement.value : null;
}

const cube = {
    faces: "DLBURF",
    states: [],
    edges: {
        D: [46, 45, 44, 38, 37, 36, 22, 21, 20, 14, 13, 12],
        L: [24, 31, 30, 40, 47, 46, 0, 7, 6, 20, 19, 18],
        B: [26, 25, 24, 8, 15, 14, 6, 5, 4, 36, 35, 34],
        U: [18, 17, 16, 34, 33, 32, 42, 41, 40, 10, 9, 8],
        R: [28, 27, 26, 16, 23, 22, 4, 3, 2, 44, 43, 42],
        F: [30, 29, 28, 32, 39, 38, 2, 1, 0, 12, 11, 10]
    },
    reset: function () {
        cube.states = ["yyyyyyyyoooooooobbbbbbbbwwwwwwwwrrrrrrrrgggggggg"];
    },
    twist: function (state, move) {
        var i, k, prevState, face = move.charAt(0), faceIndex = cube.faces.indexOf(move.charAt(0)),
            turns = move.length > 1 ? (move.charAt(1) === "2" ? 2 : 3) : 1;
        state = state.split("");
        for (i = 0; i < turns; i++) {
            prevState = state.slice(0);
            for (k = 0; k < 8; k++) { state[(faceIndex * 8) + k] = prevState[(faceIndex * 8) + ((k + 6) % 8)]; }
            for (k = 0; k < 12; k++) { state[cube.edges[face][k]] = prevState[cube.edges[face][(k + 9) % 12]]; }
        }
        return state.join("");
    },
    scramble: function () {
        var count = 0, total = 20, state, prevState = cube.states[cube.states.length - 1],
            move, moves = [], modifiers = ["", "'", "2"];
        while (count < total) {
            move = cube.faces[Math.floor(Math.random() * 6)] + modifiers[Math.floor(Math.random() * 3)];
            if (count > 0 && move.charAt(0) === moves[count - 1].charAt(0)) { continue; }
            if (count > 1 && move.charAt(0) === moves[count - 2].charAt(0) &&
                    moves[count - 1].charAt(0) === cube.faces.charAt((cube.faces.indexOf(move.charAt(0)) + 3) % 6)) {
                continue;
            }
            state = cube.twist(prevState, move);
            if (cube.states.indexOf(state) === -1) {
                moves[count] = move;
                cube.states[count] = state;
                count++;
                prevState = state;
            }
        }
        return moves;
    }
};

function updateTimer() {
    const now = Date.now();
    const diff = (now - startTime + elapsedTime) / 1000;
    timerElement.textContent = diff.toFixed(3);
}

function startTimer() {
    startTime = Date.now();
    timer = setInterval(updateTimer, 10);
    running = true;
}

function stopTimer() {
    clearInterval(timer);
    elapsedTime += Date.now() - startTime;
    running = false;
    saveTime(elapsedTime / 1000);
    elapsedTime = 0;
    running = false;
    displayScramble();
}

function resetTimer() {
    clearInterval(timer);
    elapsedTime = 0;
    timerElement.textContent = "0.000";
    running = false;
}

function displayScramble() {
    cube.reset();
    const scramble = cube.scramble();
    scrambleString = scramble.join(" ");
    document.getElementById("scramble").innerHTML = scrambleString;
    document.getElementById("scramble-display").setAttribute("scramble", scrambleString);
}

function saveTime(time) {
    const sessionId = getSessionId();

    fetch("/save_time", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ 
            time: Math.round(time * 1000), // Converting seconds to milliseconds
            scramble: scrambleString,
            session_id: sessionId  // Include session_id
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === "success") {
            console.log("Time saved successfully");
        } else {
            console.log("Failed to save time");
        }
    });
}

document.addEventListener('keyup', (event) => {
    if (event.code === 'Space') {
        event.preventDefault();
        if (!running) {
            if (elapsedTime === 0) {
                startTimer();
            } else {
                resetTimer();
            }
        } else {
            stopTimer();
        }
    }
});

displayScramble();
