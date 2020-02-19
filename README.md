# Transformer: PSII sensor files to PNG 

Converts PSII sensor files to PNG and TIFF format.
Also produces a combined histogram image and a combined false color image.  

### Sample Docker Command Line

Below is a sample command line that shows how the PSII to PNG Docker image could be run.
An explanation of the command line options used follows.
Be sure to read up on the [docker run](https://docs.docker.com/engine/reference/run/) command line for more information.

The files used in this sample command line can be found on [Google Drive](https://drive.google.com/file/d/1hJ5HBbKEPrrK566nTuVjxu2ebHliiO0R/view?usp=sharing).

```sh
docker run --rm --mount "src=/home/test,target=/mnt,type=bind" agpipeline/psii2png:2.0 --working_space /mnt --metadata /mnt/2018-06-19__02-30-22-631/30a2e41a-3af4-4ed2-8948-70bd1327d9b7_metadata_cleaned.json "/mnt/2018-06-19__02-30-22-631"
```

This example command line assumes the source files are located in the `/home/test` folder of the local machine.
The name of the image to run is `agpipeline/psii2png:2.0`.

We are using the same folder for the source files and the output files.
By using multiple `--mount` options, the source and output files can be separated.

**Docker commands** \
Everything between 'docker' and the name of the Docker image are docker commands.

- `run` indicates we want to run an image
- `--rm` automatically delete the image instance after it's run
- `--mount "src=/home/test,target=/mnt,type=bind"` mounts the `/home/test` folder to the `/mnt` folder of the running image

We mount the `/home/test` folder to the running image to make files available to the software in the image.

**Image's commands** \
The command line parameters after the image name are passed to the software inside the image.
Note that the paths provided are relative to the running image (see the --mount option specified above).

- `--working_space "/mnt"` specifies the folder to use as a workspace
- `--metadata /mnt/2018-06-19__02-30-22-631/30a2e41a-3af4-4ed2-8948-70bd1327d9b7_metadata_cleaned.json` specifies the metadata to use when processing the data
- `"/mnt/2018-06-19__02-30-22-631"` is the folder containing the sensor files to process
