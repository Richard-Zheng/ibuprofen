function changeAll(b) {
    var items = document.getElementsByName("category");
    for (let i of items) {
        i.checked = b
    }
    onSubjectCheckboxChange();
}

function onSubjectCheckboxChange() {
    var items = document.getElementsByName("category");
    var state = [];
    for (let i of items) {
        state[i.value] = i.checked;
    }

    var lsitems = document.getElementsByClassName("lesson-schedule")
    for (let i of lsitems) {
        if (state[i.dataset.subject]) {
            i.style.display = ''
        } else {
            i.style.display = 'none'
        }
    }
}