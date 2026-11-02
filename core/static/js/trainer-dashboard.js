document.addEventListener("DOMContentLoaded", function () {

    const calendarToggle =
        document.getElementById("calendarToggle");

    const calendarPopup =
        document.getElementById("calendarPopup");


    if (!calendarToggle || !calendarPopup) {
        return;
    }


    calendarToggle.addEventListener("click", function (event) {

        event.stopPropagation();

        calendarPopup.classList.toggle("show");

    });


    document.addEventListener("click", function (event) {

        if (
            !calendarPopup.contains(event.target) &&
            !calendarToggle.contains(event.target)
        ) {

            calendarPopup.classList.remove("show");

        }

    });

});