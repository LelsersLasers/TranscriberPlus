<script>
	export let api;

	let showTimestamps = false;

	let results = {
		"wip": [],  // [{'base': str, 'state': str, filename: str}, ...]
		"done": [], // [{'base': str, 'text': str, 'with_timestamps': str, 'filename': str}, ...]
	}
	let selected = null;

	setInterval(() => {
		fetch(api + "/status/")
			.then((response) => response.json())
			.then((data) => {
				results = data;
			})
			.catch((error) => {
				console.error("Error fetching status:", error);
			});
	}, 500);


	let file;

	async function uploadFile() {
        if (!file) {
            alert("Please select a file.");
            return;
        }

        const formData = new FormData();
        formData.append("file", file);

        try {
			fetch(api + "/upload/", {
				method: "POST",
				body: formData,
			})
        } catch (error) {
            console.error("Error uploading file:", error);
        }
    }
</script>


<h1>Transcriber</h1>

<h2>File Upload</h2>
<form on:submit|preventDefault={uploadFile}>
	<input
		type="file"
		accept=".mp3,.mp4,.wav"
		on:change={(e) => (file = e.target.files[0])}
	/>
	<button type="submit">Upload</button>
</form>

<h2>Status</h2>

<h3>WIP</h3>
<ul>
	{#each results.wip as item (item.base)}
		<li>{item.filename} - {item.state} ({item.base})</li>
	{/each}
</ul>

<h3>Done</h3>
<ul>
	{#each results.done as item (item.base)}
		<li>
			<button on:click={() => selected = item.base}>{item.filename}</button>
		</li>
	{/each}
</ul>


<h2>Text</h2>
<input type="checkbox" id="showTimestamps" on:change={() => showTimestamps = document.getElementById("showTimestamps").checked} />
<label for="showTimestamps">Show timestamps</label>

{#if selected}
	{#if showTimestamps}
		{@html results.done.find((item) => item.base === selected).with_timestamps}
	{:else}
		<p>{@html results.done.find((item) => item.base === selected).text}</p>
	{/if}
{/if}

<br />

