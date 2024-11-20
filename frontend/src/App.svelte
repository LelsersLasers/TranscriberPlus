<script>
	export let api;

	let showTimestamps = false;

	let loading = false;
	let loadingText = "Loading";
	setInterval(() => {
		if (loading) {
			loadingText += ".";
			const maxLen = "Loading...".length;
			if (loadingText.length > maxLen) {
				loadingText = "Loading";
			}
		}
	}, 500);

	let results = null; // { text: string, with_timestamps: string }


	let file;

	async function uploadFile() {
        if (!file) {
            alert("Please select a file.");
            return;
        }

        const formData = new FormData();
        formData.append("file", file);

        try {
			loading = true;
			fetch(api + "/upload/", {
				method: "POST",
				body: formData,
			})
				.then((response) => response.json())
				.then((data) => {
					console.log(data);
					results = data;
					loading = false;
				})
				.catch((error) => {
					console.error("Error uploading file:", error);
					results = {
						text: "Error uploading file",
						with_timestamps: "Error uploading file",
					};
					loading = false;
				});
        } catch (error) {
            console.error("Error uploading file:", error);
			results = {
				text: "Error uploading file",
				with_timestamps: "Error uploading file",
			}
			loading = false;
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


<h2>Result</h2>
<input type="checkbox" id="showTimestamps" on:change={() => showTimestamps = document.getElementById("showTimestamps").checked} />
<label for="showTimestamps">Show timestamps</label>

{#if loading}
	<p>{loadingText}</p>
{:else if results}
	{#if showTimestamps}
		{@html results.with_timestamps}
	{:else}
		<p>{results.text}</p>
	{/if}
{/if}

<br />

