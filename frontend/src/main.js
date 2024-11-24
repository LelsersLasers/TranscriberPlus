import App from './App.svelte';


const API = "http://64.98.192.13:3004";
const app = new App({
	target: document.body,
	props: {
		api: API
	}
});

export default app;