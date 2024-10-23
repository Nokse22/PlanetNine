## New page with specific kernel by name
new-notebook-name           **target**: kernel_name
new-code-name               **target**: kernel_name
new-console-name            **target**: kernel_name

## New page with specific kernel by id
new-notebook-id             **target**: kernel_id
new-code-id                 **target**: kernel_id
new-console-id              **target**: kernel_id

## Control kernel by id
shutdown-kernel-id          **target**: kernel_id
interrupt-kernel-id         **target**: kernel_id
restart-kernel-id           **target**: kernel_id

## Action for the visible page
run-cell
run-cell-and-proceed
run-line
restart-kernel-visible
restart-kernel-and-run
select-cell                 **target**: cell_index
change-kernel               **target**: page_id or "" for visible page

### Add cell to visible page
add-text-cell
add-code-cell
add-raw-cell

## Others
start-kernel

## Open file with dialog
open-notebook
open-code
open-workspace (set workspace actually)

## Open file with optimal page
open-file                   **target**: file_path

## Open file with specific page
open-file-with-text         **target**: file_path
new-browser                 **target**: starting_url or "" for empty

## Request kernel from IKernel Pages
request-kernel-id           **target**: page\_id, kernel\_id
request-kernel-name         **target**: page\_id, kernel\_name
