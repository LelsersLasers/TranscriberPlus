<script>
	import Modal from "./Modal.svelte";
	import AltModal from "./AltModal.svelte";

	export let api;

	const TRANSCRIPTION_STATE_ERROR       = -1;
	const TRANSCRIPTION_STATE_CONVERTED   = 3;
	const TRANSCRIPTION_STATE_TRANSCRIBED = 5;

	let showTextModal = false;
	let showTimestamps = false;

	let showStartModal = false;
	let language = "en";
	let model = "tiny.en";

	let results = [];
	let selected = null;

	let copy = "Copy";

	function copyText(text) {
		navigator.clipboard.writeText(text);
		copy = "Copied!";
		setTimeout(() => {
			copy = "Copy";
		}, 3000);
	}

	document.addEventListener('DOMContentLoaded', () => {
		const socket = io();

		socket.on('update', (data) => {
			results = data["transcriptions"];
			console.log(results);
		});
	});

	let file;

	function deleteFile(base) {
		try {
			fetch(api + "/delete/" + base, {
				method: "DELETE",
			})
		} catch (error) {
			console.error("Error deleting file:", error);
		}
	}

	function languageChanged(e) {
		language = e.target.value;
		if (language == "en") {
			if (model == "tiny") {
				model = "tiny.en";
			} else if (model == "base") {
				model = "base.en";
			} else if (model == "small") {
				model = "small.en";
			} else if (model == "medium") {
				model = "medium.en";
			}
		} else {
			if (model == "tiny.en") {
				model = "tiny";
			} else if (model == "base.en") {
				model = "base";
			} else if (model == "small.en") {
				model = "small";
			} else if (model == "medium.en") {
				model = "medium";
			}
		}
	}

	function modelChanged(e) {
		model = e.target.value;
		if (model == "tiny.en") {
			language = "en";
		} else if (model == "base.en") {
			language = "en";
		} else if (model == "small.en") {
			language = "en";
		} else if (model == "medium.en") {
			language = "en";
		} else {
			if (language == "en") {
				language = "auto";
			}
		}
	}

	function start() {
        if (!file) {
            alert("Please select a file.");
            return;
        }

        const formData = new FormData();
        formData.append("file", file);
		formData.append("language", language);
		formData.append("model", model);

		document.getElementById("fileInput").value = "";
		document.getElementById("fileNameDisplay").textContent = "No file chosen";

		showStartModal = false;

        try {
			fetch(api + "/upload/", {
				method: "POST",
				body: formData,
			})
        } catch (error) {
            console.error("Error uploading file:", error);
        }
    }

	function stateToColor(state) {
		switch (state) {
			case -1: return "#6c7086";
			case  1: return "#f5c2e7";
			case  2: return "#eba0ac";
			case  3: return "#fab387";
			case  4: return "#cba6f7";
			case  5: return "#74c7ec";
			case  6: return "#a6e3a1";
		}
	}

	function resultClick(base) {
		if (results.find((result) => result.base === base).state == TRANSCRIPTION_STATE_TRANSCRIBED) {
			selected = base;
			showTextModal = true;
		}
	}
</script>

<style>
.flex-center {
	display: flex;
	align-items: center;
	justify-content: center;
	width: 100%;
}

.modal-header {
	margin-top: 0em;
	margin-bottom: 0.4em;
}

#header {
	margin-top: 0.5em;
	width: 250px;
}

#main {
	background-color: #313244;
	width: 90%;
	border-radius: 2em;
	padding: 1em;
}

#new-transcription {
	padding: 0.5em 1em;
	border-radius: 0.5em;
	background-color: #94e2d5;
	color: #181825;
	font-family: "Schoolbell", cursive;
	font-weight: 400;
	font-style: normal;
	font-size: 1em;
}

#start {
	background-color: #cba6f7;
	font-family: "Schoolbell", cursive;
	font-weight: 400;
	font-style: normal;
	font-size: 1em;
	width: calc(100% - 20% - 0.5em);
}

.back {
	font-family: "Schoolbell", cursive;
	font-weight: 400;
	font-style: normal;
	background-color: #f5e0dc;
	display: block;
	font-size: 1em;
	width: 20%;
	float: right;
}

.copy {
	font-family: "Schoolbell", cursive;
	font-weight: 400;
	font-style: normal;
	background-color: #f5c2e7;
	display: block;
	font-size: 1em;
}

input {
	font-family: "Schoolbell", cursive;
	font-weight: 400;
	font-style: normal;
	font-size: 1em;
}

.bigger-margin-b {
	margin-bottom: 0.3em;
}

select {
	font-family: "Schoolbell", cursive;
	font-weight: 200;
	font-style: normal;
	font-size: 1em;
}

#no-transcriptions {
	font-style: italic;
	margin-bottom: 0.2em;
}

.result {
	padding: 0.5em;
	border-radius: 1em;
	margin-top: 0.5em;
	margin-bottom: 0.2em;
	color: #181825;

	display: flex;
	justify-content: space-between;
	align-items: center;
}

.v-stack {
	width: 100%;
	margin-left: 1em;
}

.result-text {
	margin: 0;
	padding: 0;
	display: inline-block;
}

.result-name {
	font-size: 1.2em;
	font-weight: 800;
}

.result-status {
	color: #45475a;
	font-style: italic;
}

.result-button {
	padding: 0.5em;
	border-radius: 0.5em;
	background-color: #f5e0dc;
	color: #181825;
	font-family: "Schoolbell", cursive;
	font-weight: 400;
	font-style: normal;
	font-size: 1em;
	border: none;
	float: right;
}

.pointer {
	cursor: pointer;
}
</style>

<div class="flex-center">
	<img id="header" src="/header.png" alt="header" />
	<br />
</div>

<br />

<div class="flex-center">
	<div id="main">
		<div class="flex-center">
			<button id="new-transcription" on:click={() => showStartModal = true}>New Transcription</button>
		</div>

		{#each results as result (result.base)}
			<!-- svelte-ignore a11y-click-events-have-key-events -->
			<div class="{result.state == TRANSCRIPTION_STATE_TRANSCRIBED ? 'result pointer' : 'result' }" style="background-color: {stateToColor(result.state)}" on:click={() => {resultClick(result.base)}}>
				<div class="v-stack">
					<p class="result-text result-name">{result.original_filename}</p>
					<br />
					<p class="result-text result-status">Status: {result.state_str}</p>
				</div>

				{#if result.state == TRANSCRIPTION_STATE_CONVERTED}
					<button class="result-button" on:click|stopPropagation={() => deleteFile(result.base)}>Cancel</button>
				{:else if result.state == TRANSCRIPTION_STATE_TRANSCRIBED || result.state == TRANSCRIPTION_STATE_ERROR}
					<button class="result-button" on:click|stopPropagation={() => deleteFile(result.base)}>Delete</button>
				{/if}
			</div>
		{/each}

		{#if results.length == 0}
			<div class="flex-center">
				<p id="no-transcriptions">No transcriptions yet!</p>
			</div>
		{/if}
	</div>
</div>


<br />


<AltModal bind:showModal={showTextModal}>
	{#if selected}
		<h1 class="modal-header">{results.find((result) => result.base === selected).original_filename}</h1>
	{/if}

	<input type="checkbox" id="showTimestamps" on:change={() => showTimestamps = document.getElementById("showTimestamps").checked} />
	<label for="showTimestamps">Show timestamps</label>

	{#if selected}
		 {#if showTimestamps}
		 	<br />
			{@html results.find((result) => result.base === selected).with_timestamps}
		{:else}
			<p class="bigger-margin-b">{@html results.find((result) => result.base === selected).text}</p>
		{/if}
	{/if}

	<div class="flex-center">
		<button class="copy" type="button" on:click={() => copyText(results.find((result) => result.base === selected).text)}>{copy}</button>
	</div>

	<button class="back" type="button" on:click={() => showTextModal = false}>Back</button>
	<br />
</AltModal>


<Modal bind:showModal={showStartModal}>
	<h1 class="modal-header">Upload</h1>
	<form on:submit|preventDefault={start}>
		<div style="display: inline-flex; align-items: center; gap: 0.2em; cursor: pointer; margin-bottom: 0.4em;">
			<!-- Label and input for file selection -->
			<div style="position: relative; display: inline-block; cursor: pointer;">
				<label
					for="fileInput"
					style="
						display: inline-block;
						padding: 0.4em;
						padding-left: 0.6em;
						background-color: #89dceb;
						font-size: 1em;
						border-radius: 0.5em 0 0 0.5em;
						cursor: pointer;
					"
				>
				Choose File
			  </label>
			  <input
				id="fileInput"
				type="file"
				accept=".mp3,.mp4,.wav"
				style="
				  opacity: 0;
				  position: absolute;
				  left: 0;
				  top: 0;
				  width: 100%;
				  height: 100%;
				  cursor: pointer;
				"

				on:change={(e) => {
				  file = e.target.files[0];
				  document.getElementById("fileNameDisplay").textContent = file.name;
				}}
				required
			  />
			</div>		  
			<!-- svelte-ignore a11y-click-events-have-key-events -->
			<span
			  id="fileNameDisplay"
			  style="
				font-size: 14px;
				color: #45475a;
				font-style: italic;
				overflow: hidden;
				text-overflow: ellipsis;
				white-space: nowrap;
				max-width: 250px;
				display: inline-block;
				font-size: 0.9em;
				cursor: pointer;
			  "
			  on:click={() => document.getElementById("fileInput").click()}
			>
			  No file chosen
			</span>
		  </div>
		<br />

		<label class="bigger-margin-b" for="langauge">Language:</label>
		<select class="bigger-margin-b" name="language" id="language" required on:input={(e) => languageChanged(e)} bind:value={language}>
			<option value="en" selected>English (en)</option>
			<option value="auto">Auto</option>
			<option value="fr">French (fr)</option>
			<option value="es">Spanish (es)</option>
			<option value="zh">Chinese (zh)</option>
			<option value="ar">Arabic (ar)</option>
			<option value="be">Belarusian (be)</option>
			<option value="bg">Bulgarian (bg)</option>
			<option value="bn">Bengali (bn)</option>
			<option value="ca">Catalan (ca)</option>
			<option value="cs">Czech (cs)</option>
			<option value="cy">Welsh (cy)</option>
			<option value="da">Danish (da)</option>
			<option value="de">German (de)</option>
			<option value="el">Greek (el)</option>
			<option value="it">Italian (it)</option>
			<option value="ja">Japanese (ja)</option>
			<option value="nl">Dutch (nl)</option>
			<option value="pl">Polish (pl)</option>
			<option value="pt">Portuguese (pt)</option>
			<option value="ru">Russian (ru)</option>
			<option value="sk">Slovak (sk)</option>
			<option value="sl">Slovenian (sl)</option>
			<option value="sv">Swedish (sv)</option>
			<option value="tk">Turkmen (tk)</option>
			<option value="tr">Turkish (tr)</option>
		</select>
		<br />

		<label for="model">Model:</label>
		<select name="model" id="model" required on:input={(e) => modelChanged(e)} bind:value={model}>
			<option value="tiny.en" selected>tiny.en (speed: x10, memory: ~1 GB)</option>
			<option value="base.en">base.en (speed: x7, memory: ~1 GB)</option>
			<option value="small.en">small.en (speed: x4, memory: ~2 GB)</option>
			<option value="medium.en">medium.en (speed: x2, memory: ~5 GB)</option>
			<option value="tiny">tiny (speed: x10, memory: ~1 GB)</option>
			<option value="base">base (speed: x7, memory: ~1 GB)</option>
			<option value="small">small (speed: x4, memory: ~2 GB)</option>
			<option value="medium">medium (speed: x2, memory: ~5 GB)</option>
			<option value="large">large (speed: x1, memory: ~10 GB)</option>
			<option value="turbo">turbo (speed: x8, memory: ~6 GB)</option>
		</select>
		<br />

		<br />
		<button id="start" type="submit">Start</button>
		<button class="back" type="button" on:click={() => showStartModal = false}>Back</button>
	</form>
</Modal>