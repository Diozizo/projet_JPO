let map = L.map('map').setView([48.8566, 2.3522], 12);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);

// Elements
const customDatesButton = document.getElementById('custom-dates-button');
const calendarDiv = document.getElementById('calendar');
const buttons = document.querySelectorAll(".filters");
const inputVille = document.getElementById("location-input");
const suggestionsList = document.createElement("ul");
const activeFilters = {
    statut: [],
    type: [],
    hebergement: []
};

suggestionsList.setAttribute("id", "suggestions");
inputVille.parentNode.appendChild(suggestionsList);

let date_buttons = null;
let custom_date = null;
let rMap = true;
let markers = [];
let sortOption = null;

window.onload = () => {
    document.getElementById('liste').style.display = 'none';
};

// Date selection event listeners
document.getElementById('7-days-button').addEventListener('click', () => fetchDate(7));
document.getElementById('15-days-button').addEventListener('click', () => fetchDate(15));
document.getElementById('30-days-button').addEventListener('click', () => fetchDate(30));

document.getElementById('output-type-button').addEventListener('click', changeResultType);

function fetchDate(time_period) {
    date_buttons = time_period;
    custom_date = null;
    document.getElementById('calendar').style.display = 'none';
}

function fetchCustomDate() {
    custom_date = document.getElementById('calendar-input').value;
    date_buttons = null;
    document.getElementById('calendar').style.display = 'none';
    document.getElementById('calendar-input').value = null;
}

function updateRadiusValue(value) {
    document.getElementById('radius-value').textContent = value + ' km';
}

function changeResultType() {
    rMap = !rMap;
    document.getElementById('output-type-button').textContent = rMap ? 'Liste' : 'Carte';
    document.getElementById('map').style.display = rMap ? 'block' : 'none';
    document.getElementById('liste').style.display = rMap ? 'none' : 'block';
}

// Location search
document.getElementById('location-button').addEventListener('click', () => {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition((position) =>
            fetch('/search_jpo', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    address: null, 
                    radius: document.getElementById('radius').value * 1000, 
                    date_buttons, 
                    custom_date, 
                    types: activeFilters.type,
                    statuts: activeFilters.statut,
                    hebergements: activeFilters.hebergement,
                    sortOption : sortOption,
                    longitude : position.coords.longitude,
                    latitude : position.coords.latitude,
                })
            })
            .then(response => response.json())
            .then(data => displayResults(data))
            .catch(error => console.error('Error:', error))
        );
    } else {
        alert("Votre navigateur ne supporte pas la localisation.");
    }
});

// Show/hide calendar
customDatesButton.addEventListener('click', () => {
    calendarDiv.style.display = calendarDiv.style.display === 'block' ? 'none' : 'block';
});

// Fetch results
document.getElementById('view-results-button').addEventListener('click', () => {
    const location = inputVille.value;
    const radius = document.getElementById('radius').value;
    const date_range = date_buttons;
    if (date_range === 'custom') {
        custom_date = document.getElementById('calendar-input').value || '';
    }

    fetch('/search_jpo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            address: location, 
            radius: radius * 1000, 
            date_range, 
            custom_date, 
            types: activeFilters.type,
            statuts: activeFilters.statut,
            hebergements: activeFilters.hebergement,
            sortOption : sortOption,
            longitude : null,
            latitude : null,
        })
    })
    .then(response => response.json())
    .then(data => displayResults(data))
    .catch(error => console.error('Error:', error));
});

function displayResults(data) {
    map.eachLayer(layer => { if (layer instanceof L.Marker) map.removeLayer(layer); });
    markers = [];
    document.getElementById('liste').innerHTML = '';
    const table = document.createElement('table');
    table.classList.add('result-table');
    table.innerHTML = '<thead><tr><th>Etablissement</th><th>Date</th><th>Ville</th></tr></thead>';
    const tbody = document.createElement('tbody');

    data.forEach(result => {
        const formattedDate = new Date(result.date_Date).toLocaleDateString('fr-FR');
        const row = document.createElement('tr');

        const dates = result.dates.map(date => 
            new Date(date).toLocaleDateString('fr-FR')
        ).join(', ');

        // Make Etablissement name clickable
        const establishmentLink = document.createElement('a');
        establishmentLink.href = `/etablissement/${result.id_Etablissement}`;  // The URL will redirect to the details page for this Etablissement
        establishmentLink.textContent = result.nom_Etablissement;
        establishmentLink.style.cursor = 'pointer';  // Make it look clickable

        row.innerHTML = `<td>${establishmentLink.outerHTML}</td><td>${dates}</td><td>${result.ville_Adresse}</td>`;
        tbody.appendChild(row);

        const marker = L.marker([result.latitude_Adresse, result.longitude_Adresse]).addTo(map)
            .bindPopup(`<strong>${result.nom_Etablissement}</strong><br><strong>Date: </strong>${dates}<br><strong>Ville: </strong>${result.ville_Adresse}`);
        markers.push(marker);
    });

    table.appendChild(tbody);
    document.getElementById('liste').appendChild(table);

    if (markers.length > 0) map.fitBounds(markers.map(m => m.getLatLng()));
}


function updateSuggestions(inputValue) {
    const suggestions = document.getElementById('suggestions');
    const suggestionItems = suggestions.getElementsByTagName('li');

    if (inputValue.length > 0 && suggestionItems.length > 0) {
        suggestions.style.display = 'block';
    } else {
        suggestions.style.display = 'none';
    }
}

// Autocomplete functionality
inputVille.addEventListener("input", async (e) => {
    updateSuggestions(e.target.value);
    const query = inputVille.value.trim();
    if (query.length < 2) {
        suggestionsList.innerHTML = "";
        return;
    }
    
    try {
        const response = await fetch(`/autocomplete?query=${query}`);
        const results = await response.json();

        suggestionsList.innerHTML = "";

        // Loop through the results and display them in the list
        results.forEach(suggestion => {
            // Ensure to access the correct fields: 'ville' for city and 'code_postal' for postal code
            const li = document.createElement("li");
            li.textContent = `${suggestion.ville} (${suggestion.code_postal})`; // Update to match the response format
            li.addEventListener("click", () => {
                inputVille.value = suggestion.ville;  // Set the city name in the input
                suggestionsList.innerHTML = "";  // Clear the suggestions after selecting
                suggestionsList.style.display = "none";
            });
            suggestionsList.appendChild(li);
        });
    } catch (error) {
        console.error("Erreur d'autocomplétion:", error);
    }
});


/*document.addEventListener("DOMContentLoaded", function () {
    const establishmentId = window.location.pathname.split("/").pop(); // Extract ID from URL

    fetch(`/etablissement/${establishmentId}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                document.getElementById("etablissement-info").innerHTML = "<p>Aucun établissement trouvé.</p>";
                return;
            }

            document.getElementById("nom-etablissement").textContent = data.nom_Etablissement;
            document.getElementById("adresse-complete").textContent = data.adresse_complete || "Non spécifiée";
            document.getElementById("code-uai").textContent = establishmentId;
            document.getElementById("tel-contact").textContent = data.num_tel_Etablissement || "Non disponible";
            document.getElementById("site-web").href = data.site_web_Etablissement || "#";
            document.getElementById("site-web").textContent = data.site_web_Etablissement ? "Visiter" : "Aucun site web";
            document.getElementById("description-jpo").textContent = data.description_JPO || "Pas de JPO prévue.";
            document.getElementById("type-etablissement").textContent = data.type_Etablissement;
            document.getElementById("hebergement").textContent = data.Hebergement_Etablissement || "Non spécifié";
        })
        .catch(error => console.error("Erreur lors du chargement des données:", error));
});*/


const params = new URLSearchParams(window.location.search);
const formationId = params.get("id");

fetch(`/api/formation/${formationId}`)
  .then(response => response.json())
  .then(data => {
    document.getElementById("formation-title").textContent = data.titre_Formation;
    document.getElementById("formation-niveau").textContent = data.niveau_Formation;
    document.getElementById("formation-duration").textContent = data.duree_Formation;
  });


function adjustFilter(event, filterType) {
    const filterValue = event.target.textContent;
    if (activeFilters[filterType].includes(filterValue)) {
        activeFilters[filterType].splice(activeFilters[filterType].indexOf(filterValue), 1);
        event.target.classList.remove('active');
    } else {
        activeFilters[filterType].push(filterValue);
        event.target.classList.add('active');
    }
}

document.addEventListener("DOMContentLoaded", function () {
    fetch(`/api/filters/statuts`)
        .then(response => response.json())
        .then(data => {
            const hFilter = document.getElementById('statut-filter');
            hFilter.style.display = 'none';
            data.forEach(status => {
                const option = document.createElement('button');
                option.value = status;
                option.textContent = status;
                option.onclick = (e) => adjustFilter(e, 'statut');
                hFilter.appendChild(option);
            })
        })
        .catch(error => console.error('Error:', error));
    
    fetch(`/api/filters/types`)
        .then(response => response.json())
        .then(data => {
            const hFilter = document.getElementById('type-filter');
            hFilter.style.display = 'none';
            data.forEach(type => {
                const option = document.createElement('button');
                option.value = type;
                option.textContent = type;
                option.onclick = (e) => adjustFilter(e, 'type');
                hFilter.appendChild(option);
            })
        })
        .catch(error => console.error('Error:', error));

        const hebergementFilter = document.getElementById('hebergement-filter');
        hebergementFilter.style.display = 'none';
        const hebergement = document.createElement('button');
        hebergement.value = 'yes';
        hebergement.textContent = 'internat';
        hebergement.onclick = (e) => adjustFilter(e, 'hebergement');
        hebergementFilter.appendChild(hebergement);
});

function toggleFilter(name) {
    const filter = document.getElementById(name + '-filter');
    if (filter)
        filter.style.display = filter.style.display === 'block' ? 'none' : 'block';
}


function getSortedWay() {
    sortOption = document.getElementById('sort-options').value;
    console.log(sortOption);
}
