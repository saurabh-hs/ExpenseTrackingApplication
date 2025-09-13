const searchField = document.querySelector('#searchField');
const tableOutput = document.querySelector('.table-output');
const paginationContainer = document.querySelector('.pagination-container');
const appTable = document.querySelector('.app-table');
tableOutput.style.display = "none";
const tbody = document.querySelector('.table-body');


searchField.addEventListener("keyup", (e) => {
    const searchValue = e.target.value;

    if(searchValue.trim().length > 0) {
        paginationContainer.style.display = "none";
        tbody.innerHTML = "";
        fetch("/income/search-income", {
            body: JSON.stringify({searchText: searchValue}),
            method: "POST",
        })
        .then((res) => res.json())
        .then((data) => {
            console.log("Search results:", data);
            appTable.style.display = "none";
            tableOutput.style.display = "block";

            if(data.length === 0) {
                tableOutput.innerHTML = "No results found";
            }else{

                let tableData = "";
                data.forEach(item => {
                    tableData += `
                            <tr>
                            <td>${item.amount}</td>
                            <td>${item.source}</td>
                            <td>${item.description}</td>
                            <td>${item.date}</td>
                             </tr>`;
                });
                tbody.innerHTML = tableData;
            }
        });
    }else{
        tableOutput.style.display = "none";
        appTable.style.display = "block";
        paginationContainer.style.display = "block";
    }
});