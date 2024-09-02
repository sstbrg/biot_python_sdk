# Define the file path and part size
param (
    [string]$filePath,
    [int]$partSize
)

# Open the file for reading
$stream = [System.IO.File]::OpenRead($filePath)
$partNumber = 1

# Read and split the file
while ($stream.Position -lt $stream.Length) {
    $buffer = New-Object byte[] $partSize
    $bytesRead = $stream.Read($buffer, 0, $partSize)
    $partPath = "{0}_part{1}.bin" -f $filePath, $partNumber
    [System.IO.File]::WriteAllBytes($partPath, $buffer[0..($bytesRead-1)])
    $partNumber++
}

# Close the file stream
$stream.Close()
