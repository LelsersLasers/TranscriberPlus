<script>
	export let api;

	let file;

	async function uploadFile() {
        if (!file) {
            alert("Please select a file.");
            return;
        }

        const formData = new FormData();
        formData.append("file", file);

        try {
            const response = await fetch(api + "/upload/", {
                method: "POST",
                body: formData,
            });

            if (!response.ok) {
                const errorData = await response.json();
                alert(`Error: ${errorData.error}`);
                return;
            }

            const data = await response.json();
            console.log(data);
        } catch (error) {
            console.error("Error uploading file:", error);
        }
    }
</script>





<h1>File Upload</h1>
<form on:submit|preventDefault={uploadFile}>
	<input
		type="file"
		accept=".mp3,.mp4,.wav"
		on:change={(e) => (file = e.target.files[0])}
	/>
	<button type="submit">Upload</button>
</form>





<style>
</style>