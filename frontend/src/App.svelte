<!-- <svelte:head>
	
</svelte:head> -->

<script>
	export let api;

	let showTimestamps = false;

	let results = {
		"wip": [],
		"done": [],
	};
	let selected = null;

	document.addEventListener('DOMContentLoaded', () => {
		const socket = io();

		socket.on('update', (data) => {
			console.log('update', data);
			results = data;
		});
	});

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
		<li>
			({item.extension}) {item.original_filename} - {item.state_str} ({item.base})
		</li>
	{/each}
</ul>

<h3>Done</h3>
<ul>
	{#each results.done as item (item.base)}
		<li>
			{item.original_filename} <button on:click={() => selected = item.base}>View</button>
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

