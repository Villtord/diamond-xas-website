function getDOI(doi) {
	console.log("doi +%s+", doi)
	if (doi.length == 0) {
		document.getElementById("citation_details").style.display= "none";
	}
	else {
	        var xmlhttp = new XMLHttpRequest();
		xmlhttp.overrideMimeType("application/json")
        	xmlhttp.onreadystatechange = function() {
			console.log("onreadystatechange called");
			document.getElementById("citation_details").style.display= "block";
            		if (this.readyState == 4 && this.status == 200) {
				doiJSON = JSON.parse(this.responseText);
                		document.getElementById("citation_title").innerHTML = doiJSON.message.title + " ("+ doiJSON.message['is-referenced-by-count']+" times referenced)";
            		}
			else {
                		document.getElementById("citation_title").innerHTML = "Could not find DOI: please check for correctness";
			}
        	};
        	xmlhttp.open("GET", "https://api.crossref.org/works/" + doi + "?mailto:Tom.Schoonjans@diamond.ac.uk", true);
		console.log("doi before send +%s+", doi)
                document.getElementById("citation_title").innerHTML = "Fetching...";
        	xmlhttp.send();
	}
}
