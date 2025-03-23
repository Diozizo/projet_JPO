window.onload = () => {
    fetchTableNames();
}

function fetchTableNames() {
    fetch('/get_tables')
        .then(response => response.json())
        .then(data => {
            console.log(data);
            let tableSelect = document.getElementById("tableSelect");
            data.tables.forEach(table => {
                if (!['mention', 'propose', 'se_tient_le', 'categorise', 'requiert', 'a_pour_debouche', 'disponible_en_langue', 'localisee_a', 'supporte', 'presente'].includes(table)) {
                    let option = document.createElement("option");
                    option.value = table;
                    option.text = table;
                    tableSelect.appendChild(option);
                }
            });
        });
}

function addModifyOrDeleteButtons() {
    const btnContainer = document.getElementById("dynamicForm");
    btnContainer.innerHTML = "";
    if (document.getElementById("tableSelect").value != "") {
        const modifyButton = document.createElement("button");
        modifyButton.innerHTML = "Modify";
        modifyButton.addEventListener("click", () => modifyDataForm());
        btnContainer.appendChild(modifyButton);
        const deleteButton = document.createElement("button");
        deleteButton.innerHTML = "Delete";
        deleteButton.addEventListener("click", () => deleteData());
        btnContainer.appendChild(deleteButton);
    }
}

function modifyDataForm() {
    const table = document.getElementById("tableSelect").value;
    const idTable = document.getElementById("inputIdForTable").value;

    console.log('I am here');

    if (!idTable) {
        alert("Please enter an ID to modify.");
        return;
    }

    fetch(`/get_data`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ table, idTable })
    })
    .then(response => response.json())
    .then(data => {

        if (data.success) {
            const formDiv = document.getElementById("dynamicForm");
            formDiv.innerHTML = "";

            data.columns.forEach(col => {
                let inputField = '';
                
                switch (col.type) {
                    case 'text':
                        inputField = `<label>${col.name}: <input type="text" name="${col.name}" value="${col.value}"></label><br>`;
                        break;
                    case 'integer':
                        inputField = `<label>${col.name}: <input type="number" name="${col.name}" value="${col.value}"></label><br>`;
                        break;
                    case 'boolean':
                        inputField = `<label>${col.name}: 
                                          <input type="radio" name="${col.name}" value="true" ${col.value === true ? 'checked' : ''}> Yes
                                          <input type="radio" name="${col.name}" value="false" ${col.value === false ? 'checked' : ''}> No
                                        </label><br>`;
                        break;
                    case 'date':
                        inputField = `<label>${col.name}: <input type="date" name="${col.name}" value="${col.value}"></label><br>`;
                        break;
                    default:
                        inputField = `<label>${col.name}: <input type="text" name="${col.name}" value="${col.value}"></label><br>`;
                        break;
                }

                formDiv.innerHTML += inputField;
            });

            const submitButton = `<button type="button" id="submitModifyBtn">Modify</button>`;
            formDiv.innerHTML += submitButton;

            document.getElementById('submitModifyBtn').addEventListener('click', (event) => {
                event.preventDefault();
                submitModifyData(table, idTable, table);
            });
        } else {
            alert('Error fetching data for modification.');
        }
    })
    .catch(error => {
        console.error('Error fetching data:', error);
        alert('An error occurred while fetching data.');
    });
}


function submitModifyData(table, id, primaryKey) {
    const formDiv = document.getElementById("dynamicForm");
    const formData = {};

    const inputs = formDiv.getElementsByTagName("input");
    for (let input of inputs) {
        if (input.value !== input.defaultValue) { 
            formData[input.name] = input.value === "" ? null : input.value; 
        }
    }
    console.log(primaryKey)

    if (Object.keys(formData).length === 0) {
        alert("No changes detected.");
        return;
    }

    const requestData = {
        table: table,
        idTable: id,
        primaryKey: primaryKey,  
        updated_data: formData
    };

    console.log("Request Data:", requestData);

    fetch('/modify_data', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Data modified successfully!');
        } else {
            alert('Error modifying data: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred while submitting the modification.');
    });
}

function deleteData() {
    const table = document.getElementById("tableSelect").value;
    const idTable = document.getElementById("inputIdForTable").value;

    if (!idTable) {
        alert("Please enter an ID to delete.");
        return;
    }

    fetch('/delete_data', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ table, idTable })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Data deleted successfully.');
        } else {
            alert(data.message || 'Error deleting data.');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred while deleting the data.');
    });
}