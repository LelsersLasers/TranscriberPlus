defmodule Transcriber.Repo do
  use Ecto.Repo,
    otp_app: :transcriber,
    adapter: Ecto.Adapters.SQLite3
end
