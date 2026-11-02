document.addEventListener("DOMContentLoaded", function () {

    console.log("FitConnect client dashboard loaded");

    initializeTrendChart();

});


/* =========================================================
   MARK ATTENDANCE
========================================================= */

function markAttendance() {

    const button = document.getElementById("attendanceButton");

    if (!button) {
        console.error("Attendance button not found");
        return;
    }

    const url = button.dataset.url;

    if (!url) {
        console.error("Attendance URL not found");
        return;
    }

    fetch(url)
        .then(response => {

            if (response.ok) {
                window.location.reload();
            } else {
                console.error(
                    "Failed to mark attendance:",
                    response.status
                );
            }

        })
        .catch(error => {

            console.error(
                "Error marking attendance:",
                error
            );

        });
}


/* =========================================================
   SAVE LIFESTYLE DATA
========================================================= */

function saveLifestyle(event) {

    event.preventDefault();

    const form = document.getElementById("lifestyleForm");
    const message = document.getElementById("saveMessage");

    if (!form) {
        console.error("Lifestyle form not found");
        return;
    }

    const csrfToken = form.querySelector(
        "[name=csrfmiddlewaretoken]"
    ).value;

    const formData = new FormData(form);

    fetch("/save-lifestyle/", {
        method: "POST",
        headers: {
            "X-CSRFToken": csrfToken
        },
        body: formData
    })
    .then(response => {

        if (!response.ok) {
            throw new Error(
                "Failed to save lifestyle data: " + response.status
            );
        }

        return response.json();
    })
    .then(data => {

        if (data.success) {

            message.textContent =
                "Today's health data saved successfully.";

            message.style.display = "block";

            setTimeout(() => {
                window.location.reload();
            }, 700);
        }

    })
    .catch(error => {

        console.error(
            "Error saving lifestyle data:",
            error
        );

        message.textContent =
            "Something went wrong. Please try again.";

        message.style.display = "block";
    });
}


/* =========================================================
   WEEKLY LIFESTYLE TREND
========================================================= */

function getTrendData() {

    if (typeof window.trendData === "undefined") {

        console.error(
            "Weekly trend data was not found."
        );

        return [];

    }

    return window.trendData;

}


/* =========================================================
   INITIALIZE TREND CHART
========================================================= */

function initializeTrendChart() {

    const selector =
        document.getElementById("trendMetric");

    if (!selector) {
        console.error("Trend selector not found.");
        return;
    }

    changeTrend();

}


/* =========================================================
   CHANGE TREND
========================================================= */

function changeTrend() {

    const selector =
        document.getElementById("trendMetric");

    if (!selector) {
        return;
    }

    const metric = selector.value;

    const data = getTrendData();

    if (!data.length) {
        return;
    }

    updateXAxis(data);

    updateYAxis(metric);

    drawTrendLine(
        data,
        metric
    );

    updateTrendFooter(
        data,
        metric
    );

}


/* =========================================================
   UPDATE X AXIS
========================================================= */

function updateXAxis(data) {

    const xAxis =
        document.getElementById("trendXAxis");

    if (!xAxis) {
        return;
    }

    xAxis.innerHTML = "";

    data.forEach(day => {

        const span =
            document.createElement("span");

        span.textContent = day.day;

        xAxis.appendChild(span);

    });

}


/* =========================================================
   UPDATE Y AXIS
========================================================= */

function updateYAxis(metric) {

    const yLabels = {

        sleep: [
            "10",
            "8",
            "6",
            "4",
            "2",
            "0"
        ],

        water: [
            "5",
            "4",
            "3",
            "2",
            "1",
            "0"
        ],

        nutrition: [
            "4",
            "3",
            "2",
            "1",
            "0",
            ""
        ]

    };

    const labels = yLabels[metric];

    if (!labels) {
        return;
    }

    for (let i = 0; i < labels.length; i++) {

        const element =
            document.getElementById(
                "y" + (5 - i)
            );

        if (element) {
            element.textContent =
                labels[i];
        }

    }

}


/* =========================================================
   DRAW TREND LINE
========================================================= */

function drawTrendLine(data, metric) {

    const line =
        document.getElementById("trendLine");

    const svg =
        document.getElementById("trendSvg");

    if (!line || !svg) {
        return;
    }

    const width = 700;
    const height = 260;

    const paddingX = 20;
    const paddingY = 25;

    const usableWidth =
        width - (paddingX * 2);

    const usableHeight =
        height - (paddingY * 2);


    /* -----------------------------------------------------
       Maximum value
    ----------------------------------------------------- */

    let maxValue;

    if (metric === "sleep") {

        maxValue = 10;

    } else if (metric === "water") {

        maxValue = 5;

    } else {

        maxValue = 4;

    }


    /* -----------------------------------------------------
       Create graph points
    ----------------------------------------------------- */

    const points = [];

    data.forEach((day, index) => {

        const value = day[metric];

        if (
            value === null ||
            value === undefined
        ) {
            return;
        }

        let x;

        if (data.length === 1) {

            x = width / 2;

        } else {

            x =
                paddingX +
                (
                    index /
                    (data.length - 1)
                ) *
                usableWidth;

        }

        const y =
            paddingY +
            (
                1 -
                (value / maxValue)
            ) *
            usableHeight;

        points.push({
            x: x,
            y: y,
            value: value,
            index: index
        });

    });


    /* -----------------------------------------------------
       Draw line
    ----------------------------------------------------- */

    const pointString =
        points
            .map(point =>
                `${point.x},${point.y}`
            )
            .join(" ");

    line.setAttribute(
        "points",
        pointString
    );


    /* -----------------------------------------------------
       Remove old points
    ----------------------------------------------------- */

    const oldCircles =
        svg.querySelectorAll(
            ".trend-point"
        );

    oldCircles.forEach(circle => {
        circle.remove();
    });


    /* -----------------------------------------------------
       Create new points
    ----------------------------------------------------- */

    points.forEach(point => {

        const circle =
            document.createElementNS(
                "http://www.w3.org/2000/svg",
                "circle"
            );

        circle.setAttribute(
            "cx",
            point.x
        );

        circle.setAttribute(
            "cy",
            point.y
        );

        circle.setAttribute(
            "r",
            "5"
        );

        circle.classList.add(
            "trend-point"
        );

        svg.appendChild(circle);

    });

}


/* =========================================================
   UPDATE TREND FOOTER
========================================================= */

function updateTrendFooter(data, metric) {

    const values = [];

    data.forEach(day => {

        const value = day[metric];

        if (
            value !== null &&
            value !== undefined
        ) {

            values.push({
                value: Number(value),
                day: day.day
            });

        }

    });


    const averageElement =
        document.getElementById(
            "trendAverage"
        );

    const bestElement =
        document.getElementById(
            "trendBest"
        );

    const changeElement =
        document.getElementById(
            "trendChange"
        );


    /* -----------------------------------------------------
       No data
    ----------------------------------------------------- */

    if (!values.length) {

        if (averageElement) {
            averageElement.textContent = "—";
        }

        if (bestElement) {
            bestElement.textContent = "—";
        }

        if (changeElement) {
            changeElement.textContent = "—";
        }

        return;

    }


    /* -----------------------------------------------------
       Average
    ----------------------------------------------------- */

    const total =
        values.reduce(
            (sum, item) =>
                sum + item.value,
            0
        );

    const average =
        total / values.length;


    /* -----------------------------------------------------
       Best day
    ----------------------------------------------------- */

    const best =
        values.reduce(
            (bestItem, currentItem) =>
                currentItem.value >
                bestItem.value
                    ? currentItem
                    : bestItem
        );


    /* -----------------------------------------------------
       Weekly change
    ----------------------------------------------------- */

    let change = null;

    if (values.length >= 2) {

        const first =
            values[0].value;

        const last =
            values[values.length - 1].value;

        if (first !== 0) {

            change =
                (
                    (last - first) /
                    first
                ) *
                100;

        }

    }


    /* -----------------------------------------------------
       Display average
    ----------------------------------------------------- */

    if (averageElement) {

        if (metric === "sleep") {

            averageElement.textContent =
                average.toFixed(1) + " hrs";

        } else if (metric === "water") {

            averageElement.textContent =
                average.toFixed(1) + " L";

        } else {

            const nutritionLabels = {
                1: "Poor",
                2: "Average",
                3: "Good",
                4: "Excellent"
            };

            averageElement.textContent =
                nutritionLabels[
                    Math.round(average)
                ] || "—";

        }

    }


    /* -----------------------------------------------------
       Display best day
    ----------------------------------------------------- */

    if (bestElement) {

        bestElement.textContent =
            best.day;

    }


    /* -----------------------------------------------------
       Display weekly change
    ----------------------------------------------------- */

    if (changeElement) {

        if (change === null) {

            changeElement.textContent = "—";

        } else {

            const roundedChange =
                Math.round(change);

            if (roundedChange > 0) {

                changeElement.textContent =
                    "+" + roundedChange + "%";

            } else {

                changeElement.textContent =
                    roundedChange + "%";

            }

        }

    }

}
