terraform {
  required_providers {
    google = { source = "hashicorp/google", version = "~> 5.0" }
  }
}

provider "google" {
  project = "sap-basis-copilot"
  region  = "us-east4"
}

resource "google_compute_instance" "hana_express" {
  name         = "hana-express-demo"
  machine_type = "e2-highmem-8"
  zone         = "us-east4-b"

  boot_disk {
    initialize_params {
      image = "suse-cloud/sles-15-sp4-sap"
      size  = 200
      type  = "pd-ssd"
    }
  }

  network_interface {
    network = "default"
    access_config {}
  }

  metadata = {
    ssh-keys        = "root:ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGaTgUxfD9EwGF5jeVLyPoh1W/RULPQo/45aIBKlSrep sap-basis-copilot-agent"
    enable-osconfig = "TRUE"
  }

  tags = ["hana-express", "sap-demo"]
}

output "hana_express_ip" {
  value = google_compute_instance.hana_express.network_interface[0].access_config[0].nat_ip
}
