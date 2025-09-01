console.log('loaded');
document.addEventListener('DOMContentLoaded', function () {
    const makeTableResizableAndSortable = function (table) {
        const tableBody = table.querySelector('tbody');

        // Make rows sortable
        const rowsSortable = new Sortable(tableBody, {
            animation: 150,
        });

        // Make columns and table header cells draggable using interact.js
        const headers = table.querySelectorAll('th');
        interact(headers).draggable({
            // Enable both left and right edges for dragging
            edges: { left: true, right: true, bottom: false, top: false },
            listeners: {
                start(event) {
                    const target = event.target;
                    target.classList.add('dragging');
                },
                move(event) {
                    const target = event.target;
                    const dx = event.dx;
                    target.style.transform = `translate(${dx}px)`;
                },
                end(event) {
                    const target = event.target;
                    target.style.transform = '';
                    target.classList.remove('dragging');
                },
            },
        }).resizable({
            // Enable right edge for resizing
            edges: { right: true },
            restrictEdges: {
                outer: 'parent',
            },
            restrictSize: {
                min: { width: 50 },
            },
            listeners: {
                move(event) {
                    const target = event.target;
                    const width = parseFloat(target.style.width) || 0;
                    target.style.width = width + event.dx + 'px';
                },
            },
        });
    };

    const tables = document.querySelectorAll('.resizable-table');
    tables.forEach(function (table) {
        makeTableResizableAndSortable(table);
    });


    const createResizableTable = function (table) {
        const cols = table.querySelectorAll('th');
        console.log(cols);
        [].forEach.call(cols, function (col) {
            // Add a resizer element to the column
            const resizer = document.createElement('div');
            resizer.classList.add('resizer');


            // Set the height
            resizer.style.height = `${table.offsetHeight}px`;


            col.appendChild(resizer);


            createResizableColumn(col, resizer);
        });
    };


    const createResizableColumn = function (col, resizer) {
        let x = 0;
        let w = 0;


        const mouseDownHandler = function (e) {
            x = e.clientX;


            const styles = window.getComputedStyle(col);
            w = parseInt(styles.width, 10);


            document.addEventListener('mousemove', mouseMoveHandler);
            document.addEventListener('mouseup', mouseUpHandler);


            resizer.classList.add('resizing');
        };


        const mouseMoveHandler = function (e) {
            const dx = e.clientX - x;
            col.style.width = `${w + dx}px`;
        };


        const mouseUpHandler = function () {
            resizer.classList.remove('resizing');
            document.removeEventListener('mousemove', mouseMoveHandler);
            document.removeEventListener('mouseup', mouseUpHandler);
        };


        resizer.addEventListener('mousedown', mouseDownHandler);
    };
    var id_table = 'table-responses';
    console.log(id_table);
    console.log(document.getElementById(id_table));
    createResizableTable(document.getElementById(id_table));
});