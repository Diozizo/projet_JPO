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
                let option = document.createElement("option");
                option.value = table;
                option.text = table;
                tableSelect.appendChild(option);
            });
        });
}

function fetchColumns() {
    let table = document.getElementById("tableSelect").value;
    console.log("Selected table:", table);

    fetch(`/get_columns/${table}`)
    .then(response => {
        console.log('URL requested:', `/get_columns/${table}`);
        return response.json();
    })
    .then(data => {
        console.log('Returned data:', data);
        let formDiv = document.getElementById("dynamicForm");
        formDiv.innerHTML = "";

        data.columns.forEach(col => {
            let inputField = '';
            switch (col.data_type) {
                case 'integer':
                case 'bigint':
                    inputField = `<label>${col.column_name}: <input type="number" name="${col.column_name}"></label><br>`;
                    break;
                case 'boolean':
                    inputField = `<label>${col.column_name}: 
                        <input type="radio" name="${col.column_name}" value="true"> Yes
                        <input type="radio" name="${col.column_name}" value="false"> No
                    </label><br>`;
                    break;
                case 'date':
                    inputField = `<label>${col.column_name}: <input type="date" name="${col.column_name}"></label><br>`;
                    break;
                case 'text':
                case 'varchar':
                    inputField = `<label>${col.column_name}: <input type="text" name="${col.column_name}"></label><br>`;
                    break;
                default:
                    inputField = `<label>${col.column_name}: <input type="text" name="${col.column_name}"></label><br>`;
                    break;
            }

            formDiv.innerHTML += inputField;
        });

        formDiv.innerHTML += `<button type="submit" id="submitBtn">Ajouter</button>`;
        document.getElementById('submitBtn').addEventListener('click', handleSubmit);
    });
}

function handleSubmit(event) {
    event.preventDefault();

    let table = document.getElementById("tableSelect").value;
    let formData = new FormData();
    
    const inputs = document.querySelectorAll('#dynamicForm input');
    inputs.forEach(input => {
        formData.append(input.name, input.value);
    });
    
    fetch(`/add_data/${table}`, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        console.log(data);
        if (data.success) {
            alert('Data added successfully!');
        } else {
            alert('Error adding data.');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Something went wrong.');
    });
}